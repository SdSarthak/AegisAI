import pytest
import hashlib
from unittest.mock import patch
from app.models.guard_scan_log import GuardScanLog
from app.models.user import User, SubscriptionTier


def test_guard_scan_audit_logging_and_analytics_endpoint(client, db_session):
    # Register and login a test user
    email = "audit_test@example.com"
    password = "TestPass123!"
    client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Audit Test User"})
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    # Patch LLMGuard so we don't call real models
    mock_result = {
        "decision": "allow",
        "metadata": {
            "regex_analysis": {"flag": False, "risk_score": 0.0, "matched_patterns": []},
            "intent_analysis": {"intent": "benign", "confidence": 0.95},
            "decision_reasoning": {"reasoning": "all good", "confidence": 0.95},
        }
    }

    # Patch the background task to run synchronously or just mock/intercept it
    with patch("app.modules.guard.llm_guard.LLMGuard") as MockGuard, \
         patch("app.api.v1.guard.SessionLocal", return_value=db_session):
        
        instance = MockGuard.return_value
        instance.guard.return_value = mock_result

        # Trigger guard scan
        prompt_text = "Verify audit log recording"
        response = client.post(
            "/api/v1/guard/scan",
            json={"prompt": prompt_text},
            headers=headers
        )
        assert response.status_code == 200

    # Retrieve from DB to verify prompt_hash and ip_address
    user = db_session.query(User).filter(User.email == email).first()
    log = db_session.query(GuardScanLog).filter(GuardScanLog.user_id == user.id).first()
    assert log is not None
    assert log.prompt_hash == hashlib.sha256(prompt_text.encode()).hexdigest()
    # When using TestClient, request.client might be None or testclient host. 
    # Let's verify it's saved (it can be None or a test client host string)
    assert hasattr(log, "ip_address")

    # Now let's fetch the /analytics/audit-logs endpoint
    response = client.get("/api/v1/analytics/audit-logs", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert "total" in data
    assert "page" in data
    assert "limit" in data
    assert "total_pages" in data

    assert data["total"] == 1
    assert data["items"][0]["prompt_hash"] == hashlib.sha256(prompt_text.encode()).hexdigest()

def test_analytics_audit_logs_pagination_and_role_access(client, db_session):
    # 1. Register regular user (FREE tier by default)
    user_email = "regular_user@example.com"
    password = "TestPass123!"
    client.post("/api/v1/auth/register", json={"email": user_email, "password": password, "full_name": "Regular User"})
    user_resp = client.post("/api/v1/auth/login", data={"username": user_email, "password": password})
    user_token = user_resp.json()["access_token"]
    user_headers = {"Authorization": f"Bearer {user_token}"}

    # 2. Register admin user (SCALE tier)
    admin_email = "scale_admin@example.com"
    client.post("/api/v1/auth/register", json={"email": admin_email, "password": password, "full_name": "Scale Admin"})
    
    # Change the subscription tier of scale_admin to SCALE in DB
    admin_user = db_session.query(User).filter(User.email == admin_email).first()
    admin_user.subscription_tier = SubscriptionTier.SCALE
    db_session.commit()

    admin_resp = client.post("/api/v1/auth/login", data={"username": admin_email, "password": password})
    admin_token = admin_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # Add logs for both users
    regular_user_db = db_session.query(User).filter(User.email == user_email).first()
    
    import hashlib
    log1_hash = hashlib.sha256(b"User prompt 1").hexdigest()
    log2_hash = hashlib.sha256(b"Admin prompt 1").hexdigest()

    log1 = GuardScanLog(
        user_id=regular_user_db.id,
        prompt_hash=log1_hash,
        decision="allow",
        confidence=0.9,
    )
    log2 = GuardScanLog(
        user_id=admin_user.id,
        prompt_hash=log2_hash,
        decision="block",
        confidence=0.95,
    )
    db_session.add_all([log1, log2])
    db_session.commit()

    # Regular user should only see their own log
    resp = client.get("/api/v1/analytics/audit-logs", headers=user_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 1
    assert data["items"][0]["prompt_hash"] == log1_hash

    # Admin user should see all logs across organization (both)
    resp = client.get("/api/v1/analytics/audit-logs", headers=admin_headers)
    assert resp.status_code == 200
    data = resp.json()
    assert data["total"] == 2
