"""Tests for GET /api/v1/ai-systems/export endpoint."""

import csv
import io
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
    user = User(email="export@test.com", hashed_password="x", full_name="Tester")
    db.add(user)
    db.flush()

    def override_db():
        yield db

    def override_user():
        return user

    app.dependency_overrides[get_db] = override_db
    app.dependency_overrides[get_current_user] = override_user

    with TestClient(app) as c:
        yield c, db, user

    app.dependency_overrides.clear()


class TestCSVExport:
    def test_export_returns_csv_content_type(self, client):
        c, db, user = client
        resp = c.get("/api/v1/ai-systems/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "ai_systems.csv" in resp.headers.get("content-disposition", "")

    def test_export_empty_registry_returns_header_row_only(self, client):
        c, db, user = client
        resp = c.get("/api/v1/ai-systems/export")
        reader = csv.reader(io.StringIO(resp.text))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0][0] == "id"
        assert "name" in rows[0]
        assert "risk_level" in rows[0]

    def test_export_includes_system_data(self, client):
        c, db, user = client
        system = AISystem(
            owner_id=user.id,
            name="Credit Scorer",
            use_case="Credit",
            sector="Finance",
            risk_level=RiskLevel.HIGH,
            compliance_status=ComplianceStatus.IN_PROGRESS,
            compliance_score=65.5,
        )
        db.add(system)
        db.flush()

        resp = c.get("/api/v1/ai-systems/export")
        assert resp.status_code == 200

        reader = csv.DictReader(io.StringIO(resp.text))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["name"] == "Credit Scorer"
        assert rows[0]["risk_level"] == "high"
        assert rows[0]["compliance_score"] == "65.5"

    def test_export_risk_level_filter(self, client):
        c, db, user = client
        db.add(AISystem(owner_id=user.id, name="Low Risk System", risk_level=RiskLevel.MINIMAL))
        db.add(AISystem(owner_id=user.id, name="High Risk System", risk_level=RiskLevel.HIGH))
        db.flush()

        resp = c.get("/api/v1/ai-systems/export?risk_level=minimal")
        assert resp.status_code == 200

        reader = csv.DictReader(io.StringIO(resp.text))
        rows = list(reader)
        assert all(r["risk_level"] == "minimal" for r in rows)

    def test_export_invalid_risk_level_returns_400(self, client):
        c, db, user = client
        resp = c.get("/api/v1/ai-systems/export?risk_level=banana")
        assert resp.status_code == 400
        assert "risk_level" in resp.json()["detail"].lower()
