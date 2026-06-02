import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from fastapi import status
from sqlalchemy.orm import Session

from app.core.config import settings
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


def test_scan_prompt_rejects_prompt_over_configured_length(
    authenticated_client: TestClient,
):
    oversized_prompt = "x" * (settings.GUARD_MAX_PROMPT_LENGTH + 1)

    with patch("app.modules.guard.llm_guard.LLMGuard") as mock_guard_class:
        response = authenticated_client.post(
            "/api/v1/guard/scan",
            json={"prompt": oversized_prompt},
        )

    assert response.status_code == 422
    assert "detail" in response.json()
    mock_guard_class.assert_not_called()


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
    assert len(data["items"]) == 1
    assert data["items"][0]["decision"] == "allow"
