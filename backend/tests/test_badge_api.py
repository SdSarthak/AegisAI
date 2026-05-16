import pytest
from app.models.ai_system import AISystem, RiskLevel, ComplianceStatus
from app.models.user import User


def test_get_badge_svg(client, db_session):
    # 1. Create a user (owner)
    user = User(
        email="badge-test@example.com", hashed_password="pw", company_name="Test"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # 2. Create an AI system
    system = AISystem(
        owner_id=user.id,
        name="Badge Test System",
        risk_level=RiskLevel.HIGH,
        compliance_status=ComplianceStatus.COMPLIANT,
    )
    db_session.add(system)
    db_session.commit()
    db_session.refresh(system)

    # 3. GET badge
    response = client.get(f"/badge/{system.id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    assert "<svg" in response.text
    assert "Compliant" in response.text
    assert "AegisAI" in response.text


def test_get_badge_json(client, db_session):
    # 1. Create a user (owner)
    user = User(
        email="badge-json@example.com", hashed_password="pw", company_name="Test"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    # 2. Create an AI system
    system = AISystem(
        owner_id=user.id,
        name="JSON Test System",
        risk_level=RiskLevel.LIMITED,
        compliance_status=ComplianceStatus.IN_PROGRESS,
    )
    db_session.add(system)
    db_session.commit()
    db_session.refresh(system)

    # 3. GET badge JSON
    response = client.get(f"/badge/{system.id}?format=json")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "JSON Test System"
    assert data["risk_level"] == "limited"
    assert data["compliance_status"] == "in_progress"


def test_get_badge_not_found(client):
    response = client.get("/badge/9999")
    assert response.status_code == 404
