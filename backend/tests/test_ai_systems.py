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
from uuid import uuid4
from app.models.ai_system import AISystem
from csrf_helpers import _CSRFClientWrapper  # noqa: F401  # CSRF-aware test client wrapper


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
        yield _CSRFClientWrapper(c)

    app.dependency_overrides.clear()


def create_system(client, name):
    payload = {
        "name": name,
        "description": "Test description",
    }

    response = client.post(
        "/api/v1/ai-systems/",
        json=payload,
    )

    assert response.status_code == 201
    return response.json()


def test_create_ai_system_returns_201(client):
    payload = {
        "name": f"Test System {uuid4()}",
        "description": "Test description",
    }

    response = client.post(
        "/api/v1/ai-systems/",
        json=payload,
    )

    assert response.status_code == 201

    data = response.json()

    assert data["name"] == payload["name"]
    assert data["description"] == payload["description"]


def test_list_returns_only_authenticated_users_systems(client):
    create_system(client, f"System A {uuid4()}")
    create_system(client, f"System B {uuid4()}")

    response = client.get("/api/v1/ai-systems/")

    assert response.status_code == 200

    data = response.json()

    assert "items" in data
    assert len(data["items"]) >= 2


def test_update_ai_system_fields_correctly(client):
    system = create_system(client, f"System {uuid4()}")

    response = client.put(
        f"/api/v1/ai-systems/{system['id']}",
        json={
            "name": "Updated System",
            "description": "Updated description",
        },
    )

    assert response.status_code == 200

    data = response.json()

    assert data["name"] == "Updated System"
    assert data["description"] == "Updated description"


def test_delete_ai_system_returns_204(client):
    system = create_system(client, f"Delete System {uuid4()}")

    response = client.delete(
        f"/api/v1/ai-systems/{system['id']}"
    )

    assert response.status_code == 204

    get_response = client.get(
        f"/api/v1/ai-systems/{system['id']}"
    )

    assert get_response.status_code == 404


def test_fetching_another_users_system_returns_404(db):
    owner = User(
        email="owner@test.com",
        hashed_password="x",
        full_name="Owner",
    )
    db.add(owner)
    db.flush()

    other_user = User(
        email="other@test.com",
        hashed_password="x",
        full_name="Other User",
    )
    db.add(other_user)
    db.flush()

    system = AISystem(
        owner_id=owner.id,
        name="Owner System",
    )
    db.add(system)
    db.flush()

    def override_get_db():
        yield db

    def override_user():
        return other_user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_user

    with TestClient(app) as c:
        response = c.get(
            f"/api/v1/ai-systems/{system.id}"
        )

        assert response.status_code == 404

    app.dependency_overrides.clear()