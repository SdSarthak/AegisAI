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
    user = User(email="dup@test.com", hashed_password="x", full_name="Dupe")
    db.add(user)
    db.flush()

    def override_get_db():
        yield db

    def override_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_user

    with TestClient(app) as c:
        yield c

    app.dependency_overrides.clear()


def test_create_duplicate_ai_system_rejected(client):
    c = client

    payload = {
        "name": "Unique System",
        "description": "Test",
    }

    resp1 = c.post("/api/v1/ai-systems/", json=payload)
    assert resp1.status_code == 201

    resp2 = c.post("/api/v1/ai-systems/", json=payload)
    assert resp2.status_code == 400
    assert "already exists" in resp2.json()["detail"].lower()
