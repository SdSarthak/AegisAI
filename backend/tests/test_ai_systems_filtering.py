"""Tests for search / risk_level / compliance_status query params on GET /api/v1/ai-systems."""

import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.ai_system import AISystem, RiskLevel, ComplianceStatus
from app.models.user import User


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)


@pytest.fixture
def db(engine):
    conn = engine.connect()
    tx = conn.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=conn)()
    yield session
    session.close()
    tx.rollback()
    conn.close()


@pytest.fixture
def client(db):
    user = User(email="filter@test.com", hashed_password="x", full_name="Filterer")
    db.add(user)
    db.flush()

    db.add(AISystem(owner_id=user.id, name="Alpha System", description="First tracking system", risk_level=RiskLevel.MINIMAL, compliance_status=ComplianceStatus.COMPLIANT))
    db.add(AISystem(owner_id=user.id, name="Beta System", description="Second core component", risk_level=RiskLevel.HIGH, compliance_status=ComplianceStatus.IN_PROGRESS))
    db.add(AISystem(owner_id=user.id, name="Gamma System", description="Transparency registry", risk_level=RiskLevel.LIMITED, compliance_status=ComplianceStatus.UNDER_REVIEW))
    db.flush()

    def override_db():
        yield db

    def override_user():
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    inner_client = TestClient(app)
    yield inner_client

    app.dependency_overrides.clear()


class TestAISystemsFiltering:
    def test_search_name(self, client):
        resp = client.get("/api/v1/ai-systems/?search=Alpha")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["name"] == "Alpha System"

    def test_search_description(self, client):
        resp = client.get("/api/v1/ai-systems/?search=core")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["name"] == "Beta System"

    def test_search_case_insensitive(self, client):
        resp = client.get("/api/v1/ai-systems/?search=REGISTRY")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["name"] == "Gamma System"

    def test_filter_risk_level(self, client):
        resp = client.get("/api/v1/ai-systems/?risk_level=high")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["risk_level"] == "high"

    def test_filter_compliance_status(self, client):
        resp = client.get("/api/v1/ai-systems/?compliance_status=compliant")
        assert resp.status_code == 200
        items = resp.json()["items"]
        assert len(items) == 1
        assert items[0]["compliance_status"] == "compliant"

    def test_filter_risk_level_invalid(self, client):
        resp = client.get("/api/v1/ai-systems/?risk_level=invalid_level")
        assert resp.status_code == 400

    def test_filter_compliance_status_invalid(self, client):
        resp = client.get("/api/v1/ai-systems/?compliance_status=invalid_status")
        assert resp.status_code == 400
