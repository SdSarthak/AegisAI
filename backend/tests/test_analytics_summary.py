import pytest
from datetime import datetime, timedelta
from app.models.ai_system import AISystem, RiskLevel
from app.models.compliance_snapshot import ComplianceSnapshot
from app.models.user import User


def test_analytics_summary_counts(client, db_session):
    # Register and login a test user
    email = "analytics_user@example.com"
    password = "TestPass123!"
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


def test_compliance_timeline_returns_user_system_snapshots(client, db_session):
    email = "timeline_user@example.com"
    password = "TestPass123!"
    client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Timeline User"})
    resp = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    user = db_session.query(User).filter(User.email == email).first()
    system = AISystem(owner_id=user.id, name="timeline_system", risk_level=RiskLevel.LIMITED)
    db_session.add(system)
    db_session.commit()

    snapshots = [
        ComplianceSnapshot(
            ai_system_id=system.id,
            compliance_score=75,
            compliance_status="compliant",
            risk_level="limited",
            snapshotted_at=datetime.utcnow() - timedelta(days=2),
        ),
        ComplianceSnapshot(
            ai_system_id=system.id,
            compliance_score=82,
            compliance_status="compliant",
            risk_level="limited",
            snapshotted_at=datetime.utcnow() - timedelta(days=1),
        ),
    ]
    db_session.add_all(snapshots)
    db_session.commit()

    response = client.get(f"/api/v1/analytics/compliance-timeline?system_id={system.id}&days=7", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["ai_system_id"] == system.id
    assert data["ai_system_name"] == "timeline_system"
    assert len(data["snapshots"]) == 2
    assert data["snapshots"][0]["compliance_score"] == 75
    assert data["snapshots"][1]["compliance_score"] == 82
