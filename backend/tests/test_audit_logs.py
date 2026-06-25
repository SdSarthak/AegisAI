"""Tests for AI system audit logging and history endpoint."""

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

from app.models.user import User
from app.models.ai_system import AISystem
from app.models.ai_system import ComplianceStatus


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

    session = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=conn,
    )()

    yield session

    session.close()
    tx.rollback()
    conn.close()


@pytest.fixture
def client(db):
    user = User(
        email="audit@test.com",
        hashed_password="x",
        full_name="Audit User",
    )

    db.add(user)
    db.flush()

    ai_system = AISystem(
        owner_id=user.id,
        name="Fraud Detector",
        description="Initial system",
        version="1.0",
        use_case="Fraud Detection",
        sector="Finance",
    )

    db.add(ai_system)
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


class TestAuditLogs:
    def test_ai_system_update_creates_audit_log(self, client):
        response = client.put(
            "/api/v1/ai-systems/1",
            json={
                "name": "AI Fraud Detector"
            },
        )

        assert response.status_code == 200

        history_response = client.get(
            "/api/v1/ai-systems/1/history"
        )

        assert history_response.status_code == 200

        data = history_response.json()

        assert data["total"] == 1

        log = data["items"][0]

        assert log["old_values"]["name"] == "Fraud Detector"

        assert log["new_values"]["name"] == "AI Fraud Detector"

    def test_history_endpoint_returns_paginated_response(self, client):
        response = client.get(
        "/api/v1/ai-systems/1/history?skip=0&limit=10"
        )

        assert response.status_code == 200

        data = response.json()

        assert "items" in data
        assert "total" in data
        assert "skip" in data
        assert "limit" in data

    def test_status_update_records_json_safe_audit_log(self, client):
        response = client.patch(
            "/api/v1/ai-systems/1/status",
            json={"compliance_status": ComplianceStatus.COMPLIANT.value},
        )

        assert response.status_code == 200

        history_response = client.get("/api/v1/ai-systems/1/history")

        assert history_response.status_code == 200

        data = history_response.json()

        assert data["total"] == 1

        log = data["items"][0]

        assert (
            log["old_values"]["compliance_status"]
            == ComplianceStatus.NOT_STARTED.value
        )
        assert (
            log["new_values"]["compliance_status"]
            == ComplianceStatus.COMPLIANT.value
        )
