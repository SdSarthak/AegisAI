"""Tests for sort_by / order query params on GET /api/v1/ai-systems."""

import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.ai_system import AISystem, RiskLevel
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
    user = User(email="sort@test.com", hashed_password="x", full_name="Sorter")
    db.add(user)
    db.flush()

    db.add(AISystem(owner_id=user.id, name="Alpha System", compliance_score=90.0, risk_level=RiskLevel.MINIMAL))
    db.add(AISystem(owner_id=user.id, name="Beta System", compliance_score=50.0, risk_level=RiskLevel.HIGH))
    db.add(AISystem(owner_id=user.id, name="Gamma System", compliance_score=70.0, risk_level=RiskLevel.LIMITED))
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


class TestAISystemsSorting:
    def test_default_sort_returns_200(self, client):
        resp = client.get("/api/v1/ai-systems/")
        assert resp.status_code == 200
        assert len(resp.json()) == 3

    def test_sort_by_name_asc(self, client):
        resp = client.get("/api/v1/ai-systems/?sort_by=name&order=asc")
        assert resp.status_code == 200
        names = [s["name"] for s in resp.json()]
        assert names == sorted(names)

    def test_sort_by_name_desc(self, client):
        resp = client.get("/api/v1/ai-systems/?sort_by=name&order=desc")
        assert resp.status_code == 200
        names = [s["name"] for s in resp.json()]
        assert names == sorted(names, reverse=True)

    def test_sort_by_compliance_score_desc(self, client):
        resp = client.get("/api/v1/ai-systems/?sort_by=compliance_score&order=desc")
        assert resp.status_code == 200
        scores = [s["compliance_score"] for s in resp.json() if s["compliance_score"] is not None]
        assert scores == sorted(scores, reverse=True)

    def test_invalid_sort_by_returns_400(self, client):
        resp = client.get("/api/v1/ai-systems/?sort_by=banana")
        assert resp.status_code == 400
        assert "sort_by" in resp.json()["detail"].lower()

    def test_invalid_order_returns_400(self, client):
        resp = client.get("/api/v1/ai-systems/?order=sideways")
        assert resp.status_code == 400
        assert "order" in resp.json()["detail"].lower()
