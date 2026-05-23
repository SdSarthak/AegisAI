"""Tests for the Guard API endpoints."""

import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.user import User
from app.models.guard_scan_log import GuardScanLog


@pytest.fixture(scope="module")
def engine():
    eng = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
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
        email="guard@test.com",
        hashed_password="x",
        full_name="Guard User",
    )
    db.add(user)
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


class TestGuardAPI:
    def test_scan_prompt_creates_audit_log(self, client, db):
        response = client.post(
            "/api/v1/guard/scan",
            json={"prompt": "What is the capital of France?"},
        )
        assert response.status_code == 200
        
        # Verify the audit log is created in the database
        logs = db.query(GuardScanLog).all()
        assert len(logs) == 1
        assert logs[0].decision == "allow"
        assert logs[0].user_id is not None

    def test_history_endpoint_returns_paginated_response(self, client):
        # Create a few scans
        client.post("/api/v1/guard/scan", json={"prompt": "Test 1"})
        client.post("/api/v1/guard/scan", json={"prompt": "Test 2"})

        response = client.get("/api/v1/guard/history?page=1&limit=10")
        assert response.status_code == 200
        data = response.json()
        assert "items" in data
        assert "total" in data
        assert "page" in data
        assert "limit" in data
        assert data["total"] >= 2
        assert len(data["items"]) >= 2
        assert "prompt_hash" in data["items"][0]
        assert "decision" in data["items"][0]
