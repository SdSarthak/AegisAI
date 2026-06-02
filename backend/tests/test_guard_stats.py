import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from app.models.guard_scan_log import GuardScanLog
from app.models.user import User

def _get_user_id_from_headers(headers: dict) -> int:
    from app.core.security import decode_token
    token = headers["Authorization"].split("Bearer ")[1]
    payload = decode_token(token)
    return int(payload["sub"])

@pytest.fixture
def mock_session_local(db_session):
    with patch("app.api.v1.guard.SessionLocal", return_value=db_session):
        yield

def test_scan_creates_log_row(client, auth_headers, db_session, mock_session_local):
    # Mock LLMGuard class and its guard method
    mock_result = {
        "decision": "allow",
        "metadata": {
            "regex_analysis": {"flag": False, "risk_score": 0.0, "matched_patterns": []},
            "intent_analysis": {"intent": "benign", "confidence": 0.9},
            "decision_reasoning": {"reasoning": "all good", "confidence": 0.9},
        }
    }
    
    with patch("app.modules.guard.llm_guard.LLMGuard") as MockGuard:
        instance = MockGuard.return_value
        instance.guard.return_value = mock_result
        
        response = client.post(
            "/api/v1/guard/scan",
            json={"prompt": "Hello"},
            headers=auth_headers
        )
    
    assert response.status_code == 200
    
    # Check DB
    log = db_session.query(GuardScanLog).first()
    assert log is not None
    assert log.decision == "allow"
    assert log.detection_type == "none"
    assert log.prompt_length == 5

@pytest.mark.usefixtures("auth_headers")
def test_empty_stats_response(client, auth_headers):
    response = client.get("/api/v1/guard/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_scans"] == 0
    assert "by_decision" in data
    assert data["by_decision"]["allow"]["count"] == 0

@pytest.mark.usefixtures("auth_headers")
def test_stats_aggregation(client, auth_headers, db_session):
    # Old hardcoded query removed; reading user ID dynamically from token payload instead
    user_id = _get_user_id_from_headers(auth_headers)
    
    log1 = GuardScanLog(
        user_id=user_id,
        prompt_hash="h1",
        decision="block",
        confidence=0.9,
        detection_type="ml",
        intent="malicious",
        scanned_at=datetime.now(timezone.utc)
    )
    log2 = GuardScanLog(
        user_id=user_id,
        prompt_hash="h2",
        decision="allow",
        confidence=0.95,
        detection_type="none",
        intent="benign",
        scanned_at=datetime.now(timezone.utc) - timedelta(days=1)
    )
    db_session.add_all([log1, log2])
    db_session.commit()
    
    response = client.get("/api/v1/guard/stats", params={"window": "7d"}, headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_scans"] == 2
    assert data["by_decision"]["block"]["count"] == 1
    assert data["by_decision"]["block"]["pct"] == 50.0
    assert data["by_detection_type"]["ml"]["count"] == 1

@pytest.mark.usefixtures("auth_headers")
def test_window_filtering(client, auth_headers, db_session):
    user_id = _get_user_id_from_headers(auth_headers)
    
    # Log from 2 days ago
    log = GuardScanLog(
        user_id=user_id,
        prompt_hash="old",
        decision="allow",
        confidence=0.9,
        detection_type="none",
        scanned_at=datetime.now(timezone.utc) - timedelta(days=2)
    )
    db_session.add(log)
    db_session.commit()
    
    # 24h window
    response = client.get("/api/v1/guard/stats", params={"window": "24h"}, headers=auth_headers)
    assert response.json()["total_scans"] == 0
    
    # 7d window
    response = client.get("/api/v1/guard/stats", params={"window": "7d"}, headers=auth_headers)
    assert response.json()["total_scans"] == 1

@pytest.mark.usefixtures("auth_headers", "other_user_auth_headers")
def test_unauthorized_user_access(client, auth_headers, other_user_auth_headers, db_session):
    # Read target user identity directly from standard auth headers token payload
    target_user_id = _get_user_id_from_headers(auth_headers)
    
    # Try to access target stats using other_user_auth_headers
    response = client.get(
        "/api/v1/guard/stats",
        params={"user_id": target_user_id},
        headers=other_user_auth_headers
    )
    assert response.status_code == 403

def test_admin_access(client, db_session):
    # Create regular user
    password = "TestPass123!"
    client.post("/api/v1/auth/register", json={"email": "user@example.com", "password": password, "full_name": "Regular User"})
    user = db_session.query(User).filter(User.email == "user@example.com").first()
    
    # Create admin user
    client.post("/api/v1/auth/register", json={"email": "admin@example.com", "password": password, "full_name": "Admin User"})
    
    # We need to mock the 'role' property on the User instance that get_current_user returns.
    # We can patch the model class or the dependency.
    
    with patch("app.models.user.User.role", "admin", create=True):
        response = client.post("/api/v1/auth/login", data={"username": "admin@example.com", "password": password})
        admin_token = response.json()["access_token"]
        
        response = client.get(
            "/api/v1/guard/stats",
            params={"user_id": user.id},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json()["total_scans"] == 0
