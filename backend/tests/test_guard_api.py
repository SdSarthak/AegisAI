import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.guard_scan_log import GuardScanLog
from app.api.v1.guard import user_guard_configs

@pytest.fixture(autouse=True)
def mock_session_local(db_session):
    with patch("app.api.v1.guard.SessionLocal", return_value=db_session):
        yield


@pytest.fixture(autouse=True)
def clear_in_memory_config():
    user_guard_configs.clear()
    yield
    user_guard_configs.clear()


@pytest.fixture
def test_user(db_session: Session) -> User:
    user = User(email="guard-api-test@example.com", hashed_password="hashedpassword")
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    db_session.expunge(user)
    return user


@pytest.fixture
def authenticated_client(client: TestClient, test_user: User):
    def override_current_user():
        return test_user
    
    from app.main import app
    app.dependency_overrides[get_current_user] = override_current_user
    yield client
    app.dependency_overrides.pop(get_current_user, None)


def test_get_guard_config_default(authenticated_client: TestClient):
    response = authenticated_client.get("/api/v1/guard/config")
    assert response.status_code == 200
    data = response.json()
    assert data["sanitization_level"] == "medium"
    assert data["malicious_threshold"] == 0.8
    assert data["suspicious_threshold"] == 0.5


def test_update_guard_config_success(authenticated_client: TestClient):
    payload = {
        "sanitization_level": "high",
        "malicious_threshold": 0.9,
        "suspicious_threshold": 0.6
    }
    response = authenticated_client.patch("/api/v1/guard/config", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["message"] == "Guard configuration updated successfully"
    assert data["config"]["sanitization_level"] == "high"
    assert data["config"]["malicious_threshold"] == 0.9
    assert data["config"]["suspicious_threshold"] == 0.6

    # Verify GET fetches updated config
    get_resp = authenticated_client.get("/api/v1/guard/config")
    assert get_resp.status_code == 200
    get_data = get_resp.json()
    assert get_data["sanitization_level"] == "high"


@pytest.mark.parametrize(
    "invalid_payload,expected_detail",
    [
        (
            {"sanitization_level": "invalid", "malicious_threshold": 0.8, "suspicious_threshold": 0.5},
            "Invalid sanitization level"
        ),
        (
            {"sanitization_level": "medium", "malicious_threshold": 1.2, "suspicious_threshold": 0.5},
            "malicious_threshold must be between 0 and 1"
        ),
        (
            {"sanitization_level": "medium", "malicious_threshold": 0.8, "suspicious_threshold": -0.1},
            "suspicious_threshold must be between 0 and 1"
        ),
    ]
)
def test_update_guard_config_validation(authenticated_client: TestClient, invalid_payload, expected_detail):
    response = authenticated_client.patch("/api/v1/guard/config", json=invalid_payload)
    assert response.status_code == 400
    assert response.json()["detail"] == expected_detail


def test_scan_prompt_success(authenticated_client: TestClient):
    mock_guard = MagicMock()
    mock_guard.guard.return_value = {
        "decision": "allow",
        "metadata": {
            "decision_reasoning": {
                "confidence": 0.95,
                "reasoning": "Safe prompt",
            },
            "regex_analysis": {
                "matched_patterns": [],
            },
        },
    }

    with patch("app.modules.guard.llm_guard.LLMGuard", return_value=mock_guard):
        response = authenticated_client.post("/api/v1/guard/scan", json={"prompt": "hello"})
    
    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "allow"
    assert data["confidence"] == 0.95
    assert data["reasoning"] == "Safe prompt"


def test_scan_prompt_rate_limit(authenticated_client: TestClient):
    mock_guard = MagicMock()
    mock_guard.guard.return_value = {
        "decision": "allow",
        "metadata": {
            "decision_reasoning": {"confidence": 0.9, "reasoning": "ok"},
            "regex_analysis": {"matched_patterns": []},
        },
    }

    # Clear rate limit lock before testing
    from app.api.v1.guard import _scan_attempts_by_user, _RATE_LIMIT_REQUESTS
    _scan_attempts_by_user.clear()

    with patch("app.modules.guard.llm_guard.LLMGuard", return_value=mock_guard):
        # Fire 60 requests (allowed)
        for _ in range(_RATE_LIMIT_REQUESTS):
            resp = authenticated_client.post("/api/v1/guard/scan", json={"prompt": "hello"})
            assert resp.status_code == 200
        
        # 61st request should be rate limited
        resp = authenticated_client.post("/api/v1/guard/scan", json={"prompt": "hello"})
        assert resp.status_code == 429
        assert "Rate limit exceeded" in resp.json()["detail"]
        assert "Retry-After" in resp.headers


def test_bulk_scan_success(authenticated_client: TestClient):
    mock_guard = MagicMock()
    mock_guard.guard.return_value = {
        "decision": "allow",
        "metadata": {
            "decision_reasoning": {"confidence": 0.9, "reasoning": "ok"},
            "regex_analysis": {"matched_patterns": []},
        },
    }

    from app.api.v1.guard import _scan_attempts_by_user
    _scan_attempts_by_user.clear()

    payload = {"prompts": ["prompt 1", "prompt 2", "prompt 3"]}

    with patch("app.modules.guard.llm_guard.LLMGuard", return_value=mock_guard):
        response = authenticated_client.post("/api/v1/guard/scan/batch", json=payload)
    
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["processed"] == 3
    assert len(data["results"]) == 3
    for res in data["results"]:
        assert res["decision"] == "allow"


def test_bulk_scan_validation_limit(authenticated_client: TestClient):
    # Maximum 50 prompts, so 51 prompts should fail
    payload = {"prompts": ["prompt"] * 51}
    response = authenticated_client.post("/api/v1/guard/scan/batch", json=payload)
    assert response.status_code == 400
    assert "Maximum 50 prompts allowed" in response.json()["detail"]


def test_bulk_scan_rate_limiting(authenticated_client: TestClient):
    mock_guard = MagicMock()
    mock_guard.guard.return_value = {
        "decision": "allow",
        "metadata": {
            "decision_reasoning": {"confidence": 0.9, "reasoning": "ok"},
            "regex_analysis": {"matched_patterns": []},
        },
    }

    from app.api.v1.guard import _scan_attempts_by_user
    _scan_attempts_by_user.clear()

    # limit is 60. Let's send a batch of 40.
    payload_1 = {"prompts": ["p"] * 40}
    with patch("app.modules.guard.llm_guard.LLMGuard", return_value=mock_guard):
        resp1 = authenticated_client.post("/api/v1/guard/scan/batch", json=payload_1)
        assert resp1.status_code == 200
    
    # Send another batch of 25. 40 + 25 = 65 > 60, should be blocked.
    payload_2 = {"prompts": ["p"] * 25}
    resp2 = authenticated_client.post("/api/v1/guard/scan/batch", json=payload_2)
    assert resp2.status_code == 429
    assert "Rate limit exceeded" in resp2.json()["detail"]


def test_get_guard_history(authenticated_client: TestClient, db_session: Session, test_user: User):
    # Add a scan log
    log = GuardScanLog(
        user_id=test_user.id,
        prompt_hash="dummy_hash",
        decision="allow",
        confidence=0.95,
        matched_patterns=[],
    )
    db_session.add(log)
    db_session.commit()

    response = authenticated_client.get("/api/v1/guard/history")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["decision"] == "allow"
    assert item["detection_type"] == "none"
    assert item["combined_score"] == 0.0


# ---------------------------------------------------------------------------
# Audit log tests — verify Guard scan decisions are persistently logged
# ---------------------------------------------------------------------------


def test_scan_prompt_creates_audit_log(
    authenticated_client: TestClient,
    db_session: Session,
    test_user: User,
):
    """Verify that scanning a prompt creates a GuardScanLog audit entry."""
    mock_guard = MagicMock()
    mock_guard.guard.return_value = {
        "decision": "allow",
        "metadata": {
            "decision_reasoning": {
                "confidence": 0.95,
                "reasoning": "Safe prompt",
            },
            "regex_analysis": {
                "matched_patterns": [],
            },
        },
    }

    with patch("app.modules.guard.llm_guard.LLMGuard", return_value=mock_guard):
        response = authenticated_client.post(
            "/api/v1/guard/scan", json={"prompt": "hello"}
        )

    assert response.status_code == 200

    log = db_session.query(GuardScanLog).filter(
        GuardScanLog.user_id == test_user.id
    ).first()
    assert log is not None, "No GuardScanLog audit entry was created"
    assert log.decision == "allow"
    assert log.confidence == 0.95


def test_scan_prompt_audit_log_block_decision(
    authenticated_client: TestClient,
    db_session: Session,
    test_user: User,
):
    """Verify that blocked prompts create audit logs with full metadata."""
    mock_guard = MagicMock()
    mock_guard.guard.return_value = {
        "decision": "block",
        "metadata": {
            "decision_reasoning": {
                "confidence": 0.98,
                "reasoning": "Malicious prompt detected",
            },
            "regex_analysis": {
                "matched_patterns": ["sql_injection"],
                "flag": True,
                "risk_score": 0.95,
            },
            "intent_analysis": {
                "intent": "malicious",
                "confidence": 0.97,
            },
        },
    }

    with patch("app.modules.guard.llm_guard.LLMGuard", return_value=mock_guard):
        response = authenticated_client.post(
            "/api/v1/guard/scan", json={"prompt": "DROP TABLE users; --"}
        )

    assert response.status_code == 200

    log = db_session.query(GuardScanLog).filter(
        GuardScanLog.user_id == test_user.id
    ).first()
    assert log is not None
    assert log.decision == "block"
    assert log.confidence == 0.98
    assert log.detection_type == "combined"
    assert log.regex_flag is True
    assert log.regex_score == 0.95
    assert log.intent == "malicious"
    assert log.ml_confidence == 0.97
    assert log.combined_score == 0.98
    assert log.prompt_length == len("DROP TABLE users; --")


def test_scan_prompt_audit_log_sanitize_decision(
    authenticated_client: TestClient,
    db_session: Session,
    test_user: User,
):
    """Verify that sanitized prompts create audit logs with 'sanitize' decision."""
    mock_guard = MagicMock()
    mock_guard.guard.return_value = {
        "decision": "sanitize",
        "sanitized_prompt": "****",
        "metadata": {
            "decision_reasoning": {
                "confidence": 0.85,
                "reasoning": "Suspicious content sanitized",
            },
            "regex_analysis": {
                "matched_patterns": ["profanity"],
                "flag": True,
                "risk_score": 0.70,
            },
            "intent_analysis": {
                "intent": "suspicious",
                "confidence": 0.80,
            },
        },
    }

    with patch("app.modules.guard.llm_guard.LLMGuard", return_value=mock_guard):
        response = authenticated_client.post(
            "/api/v1/guard/scan", json={"prompt": "bad word"}
        )

    assert response.status_code == 200
    data = response.json()
    assert data["decision"] == "sanitize"
    assert data["sanitized_prompt"] == "****"

    log = db_session.query(GuardScanLog).filter(
        GuardScanLog.user_id == test_user.id
    ).first()
    assert log is not None
    assert log.decision == "sanitize"
    assert log.detection_type == "combined"


def test_bulk_scan_creates_audit_logs(
    authenticated_client: TestClient,
    db_session: Session,
    test_user: User,
):
    """Verify that batch scan creates multiple GuardScanLog entries."""
    mock_guard = MagicMock()
    mock_guard.guard.return_value = {
        "decision": "allow",
        "metadata": {
            "decision_reasoning": {"confidence": 0.9, "reasoning": "ok"},
            "regex_analysis": {"matched_patterns": []},
        },
    }

    from app.api.v1.guard import _scan_attempts_by_user
    _scan_attempts_by_user.clear()

    payload = {"prompts": ["prompt 1", "prompt 2", "prompt 3"]}

    with patch("app.modules.guard.llm_guard.LLMGuard", return_value=mock_guard):
        response = authenticated_client.post(
            "/api/v1/guard/scan/batch", json=payload
        )

    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 3
    assert data["processed"] == 3

    logs = db_session.query(GuardScanLog).filter(
        GuardScanLog.user_id == test_user.id
    ).order_by(GuardScanLog.id).all()
    assert len(logs) == 3
    for log in logs:
        assert log.decision == "allow"


def test_audit_log_history_returns_full_audit_fields(
    authenticated_client: TestClient,
    db_session: Session,
    test_user: User,
):
    """Verify that /guard/history returns all audit fields in each item."""
    from datetime import datetime

    log = GuardScanLog(
        user_id=test_user.id,
        prompt_hash="abcd" * 16,
        decision="block",
        confidence=0.98,
        matched_patterns=["sql_injection"],
        detection_type="combined",
        regex_flag=True,
        regex_score=0.95,
        intent="malicious",
        ml_confidence=0.97,
        combined_score=0.98,
        prompt_length=20,
        scanned_at=datetime.utcnow(),
    )
    db_session.add(log)
    db_session.commit()

    response = authenticated_client.get("/api/v1/guard/history")
    assert response.status_code == 200
    data = response.json()
    assert data["total"] == 1
    item = data["items"][0]
    assert item["decision"] == "block"
    assert item["detection_type"] == "combined"
    assert item["regex_flag"] is True
    assert item["regex_score"] == 0.95
    assert item["intent"] == "malicious"
    assert item["ml_confidence"] == 0.97
    assert item["combined_score"] == 0.98
    assert item["prompt_length"] == 20
    assert item["scanned_at"] is not None
