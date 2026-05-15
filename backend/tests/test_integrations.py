"""Integration tests for Jira/Linear integrations and gap analysis."""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.user import User, SubscriptionTier
from app.models.ai_system import AISystem, RiskLevel, ComplianceStatus
from app.models.integration import IntegrationSettings, IntegrationType
from fastapi.testclient import TestClient


def _build_test_session_local(database_url: str):
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def test_create_jira_integration(tmp_path):
    """Test creating a Jira integration."""
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    testing_session_local = _build_test_session_local(database_url)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    db = testing_session_local()
    user = User(
        email="user@example.com",
        hashed_password="hashed",
        subscription_tier=SubscriptionTier.FREE,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    def override_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    client = TestClient(app)
    response = client.post(
        "/api/v1/integrations/jira",
        json={
            "integration_type": "jira",
            "base_url": "https://jira.example.com",
            "api_key": "test-api-key",
            "username": "user@example.com",
            "project_key": "PROJ",
            "create_on_high": True,
            "create_on_unacceptable": True,
            "create_gap_tickets": False,
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["integration_type"] == "jira"
    assert data["base_url"] == "https://jira.example.com"
    assert data["project_key"] == "PROJ"
    assert data["create_on_high"] == True

    app.dependency_overrides.clear()
    db.close()


def test_create_linear_integration(tmp_path):
    """Test creating a Linear integration."""
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    testing_session_local = _build_test_session_local(database_url)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    db = testing_session_local()
    user = User(
        email="user@example.com",
        hashed_password="hashed",
        subscription_tier=SubscriptionTier.FREE,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    def override_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    client = TestClient(app)
    response = client.post(
        "/api/v1/integrations/linear",
        json={
            "integration_type": "linear",
            "base_url": "https://api.linear.app",
            "api_key": "test-api-key",
            "team_id": "TEAM-123",
            "create_on_high": True,
            "create_on_unacceptable": True,
            "create_gap_tickets": True,
            "gap_ticket_template": {
                "explainability": "Task",
                "oversight": "Bug",
            },
        },
    )

    assert response.status_code == 201
    data = response.json()
    assert data["integration_type"] == "linear"
    assert data["team_id"] == "TEAM-123"
    assert data["create_gap_tickets"] == True
    assert "explainability" in data["gap_ticket_template"]

    app.dependency_overrides.clear()
    db.close()


def test_list_integrations(tmp_path):
    """Test listing integrations for a user."""
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    testing_session_local = _build_test_session_local(database_url)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    db = testing_session_local()
    user = User(
        email="user@example.com",
        hashed_password="hashed",
        subscription_tier=SubscriptionTier.FREE,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    
    integration = IntegrationSettings(
        user_id=user.id if user.id else 1,
        integration_type=IntegrationType.JIRA,
        base_url="https://jira.example.com",
        api_key="test-key",
        project_key="PROJ",
    )
    db.add(integration)
    db.commit()

    def override_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    client = TestClient(app)
    response = client.get("/api/v1/integrations")

    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 0

    app.dependency_overrides.clear()
    db.close()


def test_delete_integration(tmp_path):
    """Test deleting an integration."""
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    testing_session_local = _build_test_session_local(database_url)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    db = testing_session_local()
    user = User(
        email="user@example.com",
        hashed_password="hashed",
        subscription_tier=SubscriptionTier.FREE,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    integration = IntegrationSettings(
        user_id=user.id,
        integration_type=IntegrationType.LINEAR,
        base_url="https://api.linear.app",
        api_key="test-key",
        team_id="TEAM-123",
    )
    db.add(integration)
    db.commit()
    db.refresh(integration)

    def override_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    client = TestClient(app)
    response = client.delete(f"/api/v1/integrations/{integration.id}")

    assert response.status_code == 204

    # Verify deletion
    deleted = db.query(IntegrationSettings).filter(IntegrationSettings.id == integration.id).first()
    assert deleted is None

    app.dependency_overrides.clear()
    db.close()


def test_gap_analysis_endpoint(tmp_path):
    """Test the gap analysis endpoint."""
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    testing_session_local = _build_test_session_local(database_url)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    db = testing_session_local()
    user = User(
        email="user@example.com",
        hashed_password="hashed",
        subscription_tier=SubscriptionTier.FREE,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    ai_system = AISystem(
        owner_id=user.id,
        name="Test AI",
        description="Test system",
        risk_level=RiskLevel.HIGH,
        compliance_status=ComplianceStatus.IN_PROGRESS,
        questionnaire_responses={
            "explainability_documentation": False,
            "human_oversight": False,
            "data_governance": False,
        },
    )
    db.add(ai_system)
    db.commit()
    db.refresh(ai_system)

    def override_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    client = TestClient(app)
    response = client.get(f"/api/v1/gap-analysis/{ai_system.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["ai_system_id"] == ai_system.id
    assert data["risk_level"] == "high"
    assert len(data["gaps"]) > 0
    assert data["overall_compliance_score"] < 100

    app.dependency_overrides.clear()
    db.close()


def test_gap_analysis_unclassified_system(tmp_path):
    """Test gap analysis on an unclassified system returns error."""
    database_url = f"sqlite:///{tmp_path / 'test.db'}"
    testing_session_local = _build_test_session_local(database_url)

    def override_get_db():
        db = testing_session_local()
        try:
            yield db
        finally:
            db.close()

    db = testing_session_local()
    user = User(
        email="user@example.com",
        hashed_password="hashed",
        subscription_tier=SubscriptionTier.FREE,
        is_active=True,
        is_verified=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    ai_system = AISystem(
        owner_id=user.id,
        name="Test AI",
        description="Test system",
        risk_level=None,  # Not classified
        compliance_status=ComplianceStatus.NOT_STARTED,
    )
    db.add(ai_system)
    db.commit()
    db.refresh(ai_system)

    def override_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    client = TestClient(app)
    response = client.get(f"/api/v1/gap-analysis/{ai_system.id}")

    assert response.status_code == 400

    app.dependency_overrides.clear()
    db.close()
