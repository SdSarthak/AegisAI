"""Tests for server-side search and filters on GET /api/v1/ai-systems."""

import os

import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.ai_system import AISystem, ComplianceStatus, RiskLevel
from app.models.user import User


@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
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
    user = User(email="filters@test.com", hashed_password="x", full_name="Filter User")
    db.add(user)
    db.flush()

    db.add_all(
        [
            AISystem(
                owner_id=user.id,
                name="Hiring Screen",
                description="CV ranking assistant",
                risk_level=RiskLevel.HIGH,
                compliance_status=ComplianceStatus.IN_PROGRESS,
            ),
            AISystem(
                owner_id=user.id,
                name="Support Bot",
                description="Customer service helper",
                risk_level=RiskLevel.MINIMAL,
                compliance_status=ComplianceStatus.COMPLIANT,
            ),
            AISystem(
                owner_id=user.id,
                name="Claims Reviewer",
                description="Insurance triage engine",
                risk_level=RiskLevel.LIMITED,
                compliance_status=ComplianceStatus.UNDER_REVIEW,
            ),
        ]
    )
    db.flush()

    def override_db():
        yield db

    def override_user():
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_search_filters_across_name_and_description(client):
    response = client.get("/api/v1/ai-systems/?search=customer")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert [item["name"] for item in payload["items"]] == ["Support Bot"]


def test_risk_level_filter_returns_only_matching_records(client):
    response = client.get("/api/v1/ai-systems/?risk_level=high")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["name"] == "Hiring Screen"


def test_compliance_status_filter_returns_only_matching_records(client):
    response = client.get("/api/v1/ai-systems/?compliance_status=compliant")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["items"][0]["name"] == "Support Bot"


def test_combined_filters_narrow_results_before_pagination(client):
    response = client.get("/api/v1/ai-systems/?search=engine&risk_level=limited&page=1&limit=1")

    assert response.status_code == 200
    payload = response.json()
    assert payload["total"] == 1
    assert payload["page"] == 1
    assert payload["limit"] == 1
    assert [item["name"] for item in payload["items"]] == ["Claims Reviewer"]


def test_invalid_filter_values_return_400(client):
    risk_response = client.get("/api/v1/ai-systems/?risk_level=banana")
    compliance_response = client.get("/api/v1/ai-systems/?compliance_status=sideways")

    assert risk_response.status_code == 400
    assert "risk_level" in risk_response.json()["detail"].lower()
    assert compliance_response.status_code == 400
    assert "compliance_status" in compliance_response.json()["detail"].lower()
