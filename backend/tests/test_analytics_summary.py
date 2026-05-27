import pytest
from app.models.ai_system import AISystem, RiskLevel
from app.models.user import User


def test_analytics_summary_counts(client, db_session):
    # Register and login a test user
    email = "analytics_user@example.com"
    password = "password123"
    client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Analytics User"})
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    user = db_session.query(User).filter(User.email == email).first()

    # Create AI systems with different risk levels
    systems = [
        AISystem(owner_id=user.id, name="sys1", risk_level=RiskLevel.MINIMAL),
        AISystem(owner_id=user.id, name="sys2", risk_level=RiskLevel.MINIMAL),
        AISystem(owner_id=user.id, name="sys3", risk_level=RiskLevel.LIMITED),
        AISystem(owner_id=user.id, name="sys4", risk_level=RiskLevel.UNACCEPTABLE),
    ]

    db_session.add_all(systems)
    db_session.commit()

    response = client.get("/api/v1/analytics/summary", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "counts" in data
    counts = data["counts"]
    assert counts["minimal"] == 2
    assert counts["limited"] == 1
    assert counts["high"] == 0
    assert counts["unacceptable"] == 1
