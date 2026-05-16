import os
import pytest

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.ai_system import AISystem
from app.models.user import User


@pytest.fixture(scope="module")
def engine():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db(engine):
    connection = engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def user(db):
    user = User(email="owner@example.com", hashed_password="x", full_name="Owner")
    db.add(user)
    db.flush()
    return user


@pytest.fixture
def other_user(db):
    other_user = User(email="other@example.com", hashed_password="x", full_name="Other")
    db.add(other_user)
    db.flush()
    return other_user


@pytest.fixture
def client(db, user):
    def override_get_db():
        yield db

    def override_current_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    with TestClient(app) as client:
        yield client

    app.dependency_overrides.clear()


class TestAISystemsAPI:
    def test_create_ai_system_returns_201(self, client, db, user):
        payload = {
            "name": "Test AI System",
            "description": "A sample system",
            "version": "1.0",
            "use_case": "Testing",
            "sector": "Software",
        }

        response = client.post("/api/v1/ai-systems/", json=payload)

        assert response.status_code == 201
        data = response.json()
        assert data["name"] == payload["name"]
        assert data["description"] == payload["description"]
        assert data["version"] == payload["version"]
        assert data["use_case"] == payload["use_case"]
        assert data["sector"] == payload["sector"]
        assert data["id"] is not None

        persisted = db.query(AISystem).filter_by(owner_id=user.id, name=payload["name"]).first()
        assert persisted is not None
        assert persisted.description == payload["description"]

    def test_list_returns_only_authenticated_user_systems(self, client, db, user, other_user):
        owner_system = AISystem(
            owner_id=user.id,
            name="Owner System",
            description="Owned by current user",
        )
        other_system = AISystem(
            owner_id=other_user.id,
            name="Other User System",
            description="Should not be visible",
        )
        db.add(owner_system)
        db.add(other_system)
        db.flush()

        response = client.get("/api/v1/ai-systems/")

        assert response.status_code == 200
        payload = response.json()
        assert payload["total"] == 1
        assert len(payload["items"]) == 1
        assert payload["items"][0]["name"] == owner_system.name

    def test_update_system_fields_correctly(self, client, db, user):
        system = AISystem(
            owner_id=user.id,
            name="Update Target",
            description="Initial description",
            version="0.1",
            use_case="Initial use case",
            sector="Initial sector",
        )
        db.add(system)
        db.flush()

        update_payload = {
            "description": "Updated description",
            "version": "0.2",
            "use_case": "Updated use case",
            "sector": "Updated sector",
        }

        response = client.put(f"/api/v1/ai-systems/{system.id}", json=update_payload)

        assert response.status_code == 200
        updated = response.json()
        assert updated["description"] == update_payload["description"]
        assert updated["version"] == update_payload["version"]
        assert updated["use_case"] == update_payload["use_case"]
        assert updated["sector"] == update_payload["sector"]

        db.refresh(system)
        assert system.description == update_payload["description"]
        assert system.version == update_payload["version"]
        assert system.use_case == update_payload["use_case"]
        assert system.sector == update_payload["sector"]

    def test_delete_returns_204(self, client, db, user):
        system = AISystem(
            owner_id=user.id,
            name="Delete Target",
            description="To be deleted",
        )
        db.add(system)
        db.flush()

        response = client.delete(f"/api/v1/ai-systems/{system.id}")

        assert response.status_code == 204
        assert response.content == b""

        deleted = db.query(AISystem).filter_by(id=system.id).first()
        assert deleted is None

    def test_fetching_another_users_system_returns_404(self, client, db, other_user):
        other_system = AISystem(
            owner_id=other_user.id,
            name="Other User System",
            description="Belongs to a different user",
        )
        db.add(other_system)
        db.flush()

        response = client.get(f"/api/v1/ai-systems/{other_system.id}")

        assert response.status_code == 404
        assert response.json()["detail"] == "AI system not found"
