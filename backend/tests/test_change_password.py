"""Tests for POST /api/v1/auth/change-password endpoint."""

import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.security import get_current_user, get_password_hash, verify_password
from app.main import app
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
    user = User(
        email="pw@test.com",
        hashed_password=get_password_hash("OldPass1!"),
        full_name="Password Tester",
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
        yield c, user

    app.dependency_overrides.clear()


class TestChangePassword:
    def test_change_password_success(self, client):
        c, user = client
        resp = c.post(
            "/api/v1/auth/change-password",
            json={"current_password": "OldPass1!", "new_password": "NewSecret1!"},
        )
        assert resp.status_code == 200
        assert resp.json()["message"] == "Password updated successfully"
        assert verify_password("NewSecret1!", user.hashed_password)

    def test_wrong_current_password_returns_400(self, client):
        c, user = client
        resp = c.post(
            "/api/v1/auth/change-password",
            json={"current_password": "WrongPass1!", "new_password": "NewSecret1!"},
        )
        assert resp.status_code == 400
        assert "incorrect" in resp.json()["detail"].lower()

    def test_short_new_password_returns_422(self, client):
        c, user = client
        resp = c.post(
            "/api/v1/auth/change-password",
            json={"current_password": "OldPass1!", "new_password": "Ab1!"},
        )
        assert resp.status_code == 422
        assert "at least 8 characters" in str(resp.json())

    def test_missing_uppercase_returns_422(self, client):
        c, user = client
        resp = c.post(
            "/api/v1/auth/change-password",
            json={"current_password": "OldPass1!", "new_password": "alllower1!"},
        )
        assert resp.status_code == 422
        assert "uppercase" in str(resp.json())

    def test_missing_digit_returns_422(self, client):
        c, user = client
        resp = c.post(
            "/api/v1/auth/change-password",
            json={"current_password": "OldPass1!", "new_password": "AllUpper!!"},
        )
        assert resp.status_code == 422
        assert "digit" in str(resp.json())

    def test_missing_special_char_returns_422(self, client):
        c, user = client
        resp = c.post(
            "/api/v1/auth/change-password",
            json={"current_password": "OldPass1!", "new_password": "NoSpecial1A"},
        )
        assert resp.status_code == 422
        assert "special character" in str(resp.json())

    def test_multiple_missing_criteria_returns_422(self, client):
        c, user = client
        resp = c.post(
            "/api/v1/auth/change-password",
            json={"current_password": "OldPass1!", "new_password": "abc"},
        )
        assert resp.status_code == 422
        body = str(resp.json())
        assert "at least 8 characters" in body
        assert "uppercase" in body
        assert "digit" in body
        assert "special character" in body
