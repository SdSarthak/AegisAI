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
        public_badge_enabled=True
    )
    db_session.add(system)
    db_session.commit()
    db_session.refresh(system)

    # 3. GET badge
    response = client.get(f"/badge/{system.public_badge_id}")
    assert response.status_code == 200
    assert response.headers["content-type"] == "image/svg+xml"
    assert "Cache-Control" in response.headers
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
        public_badge_enabled=True
    )
    db_session.add(system)
    db_session.commit()
    db_session.refresh(system)

    # 3. GET badge JSON
    response = client.get(f"/badge/{system.public_badge_id}?format=json")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "JSON Test System"
    assert data["risk_level"] == "limited"
    assert data["compliance_status"] == "in_progress"
    assert data["public_badge_id"] == system.public_badge_id


def test_get_badge_disabled(client, db_session):
    user = User(
        email="badge-disabled@example.com", hashed_password="pw", company_name="Test"
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    system = AISystem(
        owner_id=user.id,
        name="Disabled Badge System",
        risk_level=RiskLevel.MINIMAL,
        compliance_status=ComplianceStatus.NOT_STARTED,
        public_badge_enabled=False
    )
    db_session.add(system)
    db_session.commit()
    db_session.refresh(system)

    response = client.get(f"/badge/{system.public_badge_id}")
    assert response.status_code == 404

def test_get_badge_not_found(client):
    response = client.get("/badge/not-a-real-uuid")
    assert response.status_code == 404

def test_get_badge_rate_limiting(client, db_session, monkeypatch):
    # Mock the rate limiter to simulate rate limit exceeded
    from app.core.rate_limit import DistributedRateLimiter
    def mock_check_and_consume(*args, **kwargs):
        return True, 30  # limited, retry_after

    monkeypatch.setattr(DistributedRateLimiter, "check_and_consume", mock_check_and_consume)
    
    response = client.get("/badge/some-uuid")
    assert response.status_code == 429
    assert response.headers["Retry-After"] == "30"

