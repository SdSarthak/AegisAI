import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime, timedelta, timezone
from app.models.guard_scan_log import GuardScanLog
from app.models.user import User

@pytest.fixture
def auth_headers(client):
    email = "test_stats@example.com"
    password = "TestPass123!"
    client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Test User"})
    response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def other_user_auth_headers(client):
    email = "other@example.com"
    password = "TestPass123!"
    client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Other User"})
    response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}

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

def test_empty_stats_response(client, auth_headers):
    response = client.get("/api/v1/guard/stats", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["total_scans"] == 0
    assert "by_decision" in data
    assert data["by_decision"]["allow"]["count"] == 0

def test_stats_aggregation(client, auth_headers, db_session):
    # Manually add some logs
    user = db_session.query(User).filter(User.email == "test_stats@example.com").first()
    
    log1 = GuardScanLog(
        user_id=user.id,
        prompt_hash="h1",
        decision="block",
        confidence=0.9,
        detection_type="ml",
        intent="malicious",
        scanned_at=datetime.utcnow()
    )
    log2 = GuardScanLog(
        user_id=user.id,
        prompt_hash="h2",
        decision="allow",
        confidence=0.95,
        detection_type="none",
        intent="benign",
        scanned_at=datetime.utcnow() - timedelta(days=1)
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

def test_window_filtering(client, auth_headers, db_session):
    user = db_session.query(User).filter(User.email == "test_stats@example.com").first()
    
    # Log from 2 days ago
    log = GuardScanLog(
        user_id=user.id,
        prompt_hash="old",
        decision="allow",
        confidence=0.9,
        detection_type="none",
        scanned_at=datetime.utcnow() - timedelta(days=2)
    )
    db_session.add(log)
    db_session.commit()
    
    # 24h window
    response = client.get("/api/v1/guard/stats", params={"window": "24h"}, headers=auth_headers)
    assert response.json()["total_scans"] == 0
    
    # 7d window
    response = client.get("/api/v1/guard/stats", params={"window": "7d"}, headers=auth_headers)
    assert response.json()["total_scans"] == 1

def test_unauthorized_user_access(client, auth_headers, other_user_auth_headers, db_session):
    user = db_session.query(User).filter(User.email == "test_stats@example.com").first()
    
    # Try to access test_stats@example.com stats using other@example.com headers
    response = client.get(
        "/api/v1/guard/stats",
        params={"user_id": user.id},
        headers=other_user_auth_headers
    )
    assert response.status_code == 403

def test_admin_access(client, db_session):
    # Create regular user
    client.post("/api/v1/auth/register", json={"email": "user@example.com", "password": "TestPass123!", "full_name": "Regular User"})
    user = db_session.query(User).filter(User.email == "user@example.com").first()
    
    # Create admin user
    client.post("/api/v1/auth/register", json={"email": "admin@example.com", "password": "AdminPass123!", "full_name": "Admin User"})
    
    # We need to mock the 'role' property on the User instance that get_current_user returns.
    # We can patch the model class or the dependency.
    
    with patch("app.models.user.User.role", "admin", create=True):
        response = client.post("/api/v1/auth/login", data={"username": "admin@example.com", "password": "AdminPass123!"})
        admin_token = response.json()["access_token"]
        
        response = client.get(
            "/api/v1/guard/stats",
            params={"user_id": user.id},
            headers={"Authorization": f"Bearer {admin_token}"}
        )
        assert response.status_code == 200
        assert response.json()["total_scans"] == 0
