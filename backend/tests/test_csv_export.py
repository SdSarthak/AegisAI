"""Tests for GET /api/v1/ai-systems/export endpoint."""

import csv
import io
import json
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
from app.models.ai_system import AISystem, ComplianceStatus, RiskLevel
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
    def _csv_text(self, response):
        return response.content.decode("utf-8-sig")

    def test_export_returns_csv_content_type(self, client):
        c, db, user = client
        resp = c.get("/api/v1/ai-systems/export")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert "ai_systems.csv" in resp.headers.get("content-disposition", "")
        assert resp.content.startswith(b"\xef\xbb\xbf")

    def test_export_empty_registry_returns_header_row_only(self, client):
        c, db, user = client
        resp = c.get("/api/v1/ai-systems/export")
        reader = csv.reader(io.StringIO(self._csv_text(resp)))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0][0] == "id"
        assert "name" in rows[0]
        assert "risk_classification" in rows[0]
        assert "valid_until" in rows[0]
        assert "updated_at" in rows[0]

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

        reader = csv.DictReader(io.StringIO(self._csv_text(resp)))
        rows = list(reader)
        assert len(rows) == 1
        assert rows[0]["name"] == "Credit Scorer"
        assert rows[0]["risk_level"] == "high"
        assert rows[0]["risk_classification"] == "high"
        assert rows[0]["compliance_score"] == "65.5"
        assert "updated_at" in rows[0]

    def test_export_risk_level_filter(self, client):
        c, db, user = client
        db.add(AISystem(owner_id=user.id, name="Low Risk System", risk_level=RiskLevel.MINIMAL))
        db.add(AISystem(owner_id=user.id, name="High Risk System", risk_level=RiskLevel.HIGH))
        db.flush()

        resp = c.get("/api/v1/ai-systems/export?risk_level=minimal")
        assert resp.status_code == 200

        reader = csv.DictReader(io.StringIO(self._csv_text(resp)))
        rows = list(reader)
        assert all(r["risk_level"] == "minimal" for r in rows)
        assert all(r["risk_classification"] == "minimal" for r in rows)

    def test_export_sanitizes_formula_injection_name(self, client):
        c, db, user = client
        db.add(AISystem(
            owner_id=user.id,
            name="=HYPERLINK(\"http://evil.com\",\"Click me\")",
            risk_level=RiskLevel.MINIMAL,
        ))
        db.flush()

        resp = c.get("/api/v1/ai-systems/export")
        reader = csv.DictReader(io.StringIO(self._csv_text(resp)))
        rows = list(reader)
        assert rows[0]["name"].startswith("'=HYPERLINK")

    def test_export_sanitizes_plus_prefix(self, client):
        c, db, user = client
        db.add(AISystem(
            owner_id=user.id,
            name="Normal",
            description="+SUM(A1:A10)",
            risk_level=RiskLevel.MINIMAL,
        ))
        db.flush()

        resp = c.get("/api/v1/ai-systems/export")
        reader = csv.DictReader(io.StringIO(self._csv_text(resp)))
        rows = list(reader)
        assert rows[0]["description"].startswith("'+SUM")

    def test_export_sanitizes_dash_prefix(self, client):
        c, db, user = client
        db.add(AISystem(
            owner_id=user.id,
            name="Normal",
            use_case="-1+1",
            risk_level=RiskLevel.MINIMAL,
        ))
        db.flush()

        resp = c.get("/api/v1/ai-systems/export")
        reader = csv.DictReader(io.StringIO(self._csv_text(resp)))
        rows = list(reader)
        assert rows[0]["use_case"].startswith("'-")

    def test_export_sanitizes_at_prefix(self, client):
        c, db, user = client
        db.add(AISystem(
            owner_id=user.id,
            name="Normal",
            sector="@SUM(A1)",
            risk_level=RiskLevel.MINIMAL,
        ))
        db.flush()

        resp = c.get("/api/v1/ai-systems/export")
        reader = csv.DictReader(io.StringIO(self._csv_text(resp)))
        rows = list(reader)
        assert rows[0]["sector"].startswith("'@")

    def test_export_does_not_escape_normal_values(self, client):
        c, db, user = client
        db.add(AISystem(
            owner_id=user.id,
            name="Safe Name",
            description="Just text",
            use_case="Analysis",
            sector="Tech",
            risk_level=RiskLevel.MINIMAL,
        ))
        db.flush()

        resp = c.get("/api/v1/ai-systems/export")
        reader = csv.DictReader(io.StringIO(self._csv_text(resp)))
        rows = list(reader)
        assert rows[0]["name"] == "Safe Name"
        assert rows[0]["description"] == "Just text"
        assert rows[0]["use_case"] == "Analysis"
        assert rows[0]["sector"] == "Tech"

    def test_export_invalid_risk_level_returns_400(self, client):
        c, db, user = client
        resp = c.get("/api/v1/ai-systems/export?risk_level=banana")
        assert resp.status_code == 400
        assert "risk_level" in resp.json()["detail"].lower()

    def test_export_json_format_returns_payload(self, client):
        c, db, user = client
        db.add(
            AISystem(
                owner_id=user.id,
                name="JSON System",
                description="For json export",
                sector="Finance",
                use_case="Risk scoring",
                risk_level=RiskLevel.LIMITED,
                compliance_status=ComplianceStatus.COMPLIANT,
                compliance_score=88.8,
            )
        )
        db.flush()

        resp = c.get("/api/v1/ai-systems/export?format=json")
        assert resp.status_code == 200
        assert "application/json" in resp.headers["content-type"]

        payload = json.loads(resp.text)
        assert isinstance(payload, list)
        assert len(payload) == 1
        row = payload[0]
        assert row["name"] == "JSON System"
        assert row["risk_classification"] == "limited"
        assert row["risk_level"] == "limited"
        assert row["compliance_status"] == "compliant"
        assert row["compliance_score"] == 88.8
        assert "created_at" in row
        assert "updated_at" in row

    def test_export_invalid_format_returns_400(self, client):
        c, db, user = client
        resp = c.get("/api/v1/ai-systems/export?format=xml")
        assert resp.status_code == 400
        assert "format" in resp.json()["detail"].lower()
