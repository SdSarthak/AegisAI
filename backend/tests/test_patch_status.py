"""Tests for PATCH /api/v1/ai-systems/{id}/status endpoint."""

import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.ai_system import AISystem, ComplianceStatus
from app.models.user import User


@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
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
    user = User(email="patch@test.com", hashed_password="x", full_name="Patcher")
    db.add(user)
    db.flush()

    system = AISystem(
        owner_id=user.id,
        name="Status Test System",
        compliance_status=ComplianceStatus.NOT_STARTED,
    )
    db.add(system)
    db.flush()

    def override_db():
        yield db

    def override_user():
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    with TestClient(app) as c:
        c.get("/api/v1/auth/csrf-token")
        yield c, system

    app.dependency_overrides.clear()


class TestPatchStatus:
    def test_patch_status_success(self, client):
        c, system = client
        resp = c.patch(
            f"/api/v1/ai-systems/{system.id}/status",
            json={"compliance_status": "compliant"},
        )
        assert resp.status_code == 200
        assert resp.json()["compliance_status"] == "compliant"

    def test_patch_status_reflected_in_get(self, client):
        c, system = client

        # Update status
        patch_resp = c.patch(
            f"/api/v1/ai-systems/{system.id}/status",
            json={"compliance_status": "compliant"},
        )

        assert patch_resp.status_code == 200

        # Fetch updated system
        get_resp = c.get(f"/api/v1/ai-systems/{system.id}")

        assert get_resp.status_code == 200

        data = get_resp.json()

        assert data["compliance_status"] == "compliant"

    def test_patch_status_other_fields_unchanged(self, client):
        c, system = client
        resp = c.patch(
            f"/api/v1/ai-systems/{system.id}/status",
            json={"compliance_status": "in_progress"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["name"] == "Status Test System"
        assert data["compliance_status"] == "in_progress"

    def test_patch_status_404_on_unknown_id(self, client):
        c, system = client
        resp = c.patch(
            "/api/v1/ai-systems/99999/status",
            json={"compliance_status": "compliant"},
        )
        assert resp.status_code == 404

    def test_patch_status_invalid_value_returns_422(self, client):
        c, system = client
        resp = c.patch(
            f"/api/v1/ai-systems/{system.id}/status",
            json={"compliance_status": "banana"},
        )
        assert resp.status_code == 422

    def test_patch_other_users_system_returns_404(self, db):
        # Create owner user
        owner = User(
            email="owner@test.com",
            hashed_password="x",
            full_name="Owner",
        )

        db.add(owner)
        db.flush()

        # Create another user
        other_user = User(
            email="other@test.com",
            hashed_password="x",
            full_name="Other User",
        )

        db.add(other_user)
        db.flush()

        # Create system owned by owner
        system = AISystem(
            owner_id=owner.id,
            name="Owner System",
            compliance_status=ComplianceStatus.NOT_STARTED,
        )

        db.add(system)
        db.flush()

        def override_db():
            yield db

        def override_user():
            return other_user

        app.dependency_overrides[get_db] = override_db
        app.dependency_overrides[get_current_user] = override_user

        with TestClient(app) as c:
            resp = c.patch(
                f"/api/v1/ai-systems/{system.id}/status",
                json={"compliance_status": "compliant"},
            )

            assert resp.status_code == 404

        app.dependency_overrides.clear()
