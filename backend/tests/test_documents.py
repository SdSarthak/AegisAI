"""
Unit tests for document generation — all 3 template types.
Refactored with pytest fixtures, parametrization, and edge-case coverage.
"""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker
from app.core.security import get_current_user, get_password_hash, create_access_token
from app.core.database import get_db
from app.main import app
from app.models.user import User, SubscriptionTier


@pytest.fixture
def shared_session(db_engine):
    """Single shared session for the whole test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()

    # Override DB for all requests
    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    yield session

    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.pop(get_db, None)


@pytest.fixture
def api_client(shared_session):
    """A single TestClient that uses the shared session."""
    return TestClient(app, raise_server_exceptions=False)


@pytest.fixture
def user1(shared_session):
    """Create user1 in DB and return (user, auth_headers)."""
    u = User(
        email="docuser1@example.com",
        hashed_password=get_password_hash("pass123"),
        full_name="Doc User 1",
        company_name="Company 1",
        subscription_tier=SubscriptionTier.FREE,
        is_active=True,
        is_verified=True,
    )
    shared_session.add(u)
    shared_session.flush()

    # Override auth to return this user
    app.dependency_overrides[get_current_user] = lambda: u
    token = create_access_token(data={"sub": str(u.id)})
    headers = {"Authorization": f"Bearer {token}"}
    return u, headers


@pytest.fixture
def user2(shared_session, user1):
    """Create user2 in DB and return (user, auth_headers)."""
    u = User(
        email="docuser2@example.com",
        hashed_password=get_password_hash("pass123"),
        full_name="Doc User 2",
        company_name="Company 2",
        subscription_tier=SubscriptionTier.FREE,
        is_active=True,
        is_verified=True,
    )
    shared_session.add(u)
    shared_session.flush()
    token = create_access_token(data={"sub": str(u.id)})
    headers = {"Authorization": f"Bearer {token}"}
    return u, headers


@pytest.fixture
def ai_system(api_client, user1, shared_session):
    """Create AI system as user1."""
    u1, headers1 = user1
    app.dependency_overrides[get_current_user] = lambda: u1
    response = api_client.post(
        "/api/v1/ai-systems/",
        json={"name": "Test AI System", "description": "A test system"},
        headers=headers1
    )
    assert response.status_code == 201
    return response.json()["id"]


@pytest.fixture
def generated_document(api_client, user1, ai_system, shared_session):
    """Generate a document as user1."""
    u1, headers1 = user1
    app.dependency_overrides[get_current_user] = lambda: u1
    response = api_client.post(
        "/api/v1/documents/generate",
        json={"ai_system_id": ai_system, "document_type": "technical_documentation"},
        headers=headers1
    )
    assert response.status_code == 201
    return response.json()

def as_user(user_obj):
    """Switch the current user override."""
    app.dependency_overrides[get_current_user] = lambda: user_obj

def test_list_document_templates(api_client, user1):
    u1, h1 = user1
    as_user(u1)
    response = api_client.get("/api/v1/documents/templates", headers=h1)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3
    template_types = {t["type"] for t in data}
    assert "technical_documentation" in template_types
    assert "risk_assessment" in template_types
    assert "conformity_declaration" in template_types
    for template in data:
        assert template["name"]
        assert template["description"]


def test_list_templates_requires_auth(api_client, shared_session):
    """Templates endpoint must reject unauthenticated requests."""
    app.dependency_overrides.pop(get_current_user, None)
    response = api_client.get("/api/v1/documents/templates")
    assert response.status_code == 401


@pytest.mark.parametrize("doc_type", [
    "technical_documentation",
    "risk_assessment",
    "conformity_declaration",
])
def test_generate_document_all_types(api_client, user1, ai_system, doc_type):
    u1, h1 = user1
    as_user(u1)
    response = api_client.post(
        "/api/v1/documents/generate",
        json={"ai_system_id": ai_system, "document_type": doc_type},
        headers=h1
    )
    assert response.status_code == 201
    data = response.json()
    assert data["document_type"] == doc_type
    assert data["content"] is not None
    assert len(data["content"]) > 0
    assert "id" in data
    assert "title" in data


def test_generate_invalid_document_type(api_client, user1, ai_system):
    u1, h1 = user1
    as_user(u1)
    response = api_client.post(
        "/api/v1/documents/generate",
        json={"ai_system_id": ai_system, "document_type": "invalid_type"},
        headers=h1
    )
    assert response.status_code == 422


def test_generate_missing_ai_system_id(api_client, user1):
    u1, h1 = user1
    as_user(u1)
    response = api_client.post(
        "/api/v1/documents/generate",
        json={"document_type": "technical_documentation"},
        headers=h1
    )
    assert response.status_code == 422


def test_generate_missing_document_type(api_client, user1, ai_system):
    u1, h1 = user1
    as_user(u1)
    response = api_client.post(
        "/api/v1/documents/generate",
        json={"ai_system_id": ai_system},
        headers=h1
    )
    assert response.status_code == 422


def test_generate_empty_payload(api_client, user1):
    u1, h1 = user1
    as_user(u1)
    response = api_client.post("/api/v1/documents/generate", json={}, headers=h1)
    assert response.status_code == 422


def test_generate_document_requires_auth(api_client, shared_session):
    app.dependency_overrides.pop(get_current_user, None)
    response = api_client.post(
        "/api/v1/documents/generate",
        json={"ai_system_id": 1, "document_type": "technical_documentation"}
    )
    assert response.status_code == 401


def test_generate_document_invalid_token(api_client, shared_session):
    app.dependency_overrides.pop(get_current_user, None)
    response = api_client.post(
        "/api/v1/documents/generate",
        json={"ai_system_id": 1, "document_type": "technical_documentation"},
        headers={"Authorization": "Bearer invalidtoken123"}
    )
    assert response.status_code == 401


def test_generate_for_nonexistent_system(api_client, user1):
    u1, h1 = user1
    as_user(u1)
    response = api_client.post(
        "/api/v1/documents/generate",
        json={"ai_system_id": 99999, "document_type": "technical_documentation"},
        headers=h1
    )
    assert response.status_code == 404


def test_generate_for_another_users_system(api_client, user1, user2, ai_system):
    u1, h1 = user1
    u2, h2 = user2
    # Switch to user2
    as_user(u2)
    response = api_client.post(
        "/api/v1/documents/generate",
        json={"ai_system_id": ai_system, "document_type": "technical_documentation"},
        headers=h2
    )
    assert response.status_code == 404



def test_create_document(api_client, user1, ai_system):
    u1, h1 = user1
    as_user(u1)
    response = api_client.post(
        "/api/v1/documents/",
        json={
            "title": "My Test Doc",
            "document_type": "technical_documentation",
            "ai_system_id": ai_system,
            "content": "Some content here"
        },
        headers=h1
    )
    assert response.status_code == 201
    data = response.json()
    assert data["title"] == "My Test Doc"
    assert data["content"] == "Some content here"


def test_list_documents(api_client, user1, generated_document):
    u1, h1 = user1
    as_user(u1)
    response = api_client.get("/api/v1/documents/", headers=h1)
    assert response.status_code == 200
    data = response.json()
    assert "items" in data
    assert data["total"] >= 1


def test_get_document_by_id(api_client, user1, generated_document):
    u1, h1 = user1
    as_user(u1)
    doc_id = generated_document["id"]
    response = api_client.get(f"/api/v1/documents/{doc_id}", headers=h1)
    assert response.status_code == 200
    assert response.json()["id"] == doc_id


def test_get_document_not_found(api_client, user1):
    u1, h1 = user1
    as_user(u1)
    response = api_client.get("/api/v1/documents/99999", headers=h1)
    assert response.status_code == 404


def test_get_document_wrong_user(api_client, user1, user2, generated_document):
    u1, h1 = user1
    u2, h2 = user2
    doc_id = generated_document["id"]
    # Switch to user2
    as_user(u2)
    response = api_client.get(f"/api/v1/documents/{doc_id}", headers=h2)
    assert response.status_code == 404


def test_update_document(api_client, user1, generated_document):
    u1, h1 = user1
    as_user(u1)
    doc_id = generated_document["id"]
    response = api_client.put(
        f"/api/v1/documents/{doc_id}",
        json={"content": "Updated content"},
        headers=h1
    )
    assert response.status_code == 200
    assert response.json()["content"] == "Updated content"


def test_update_document_wrong_user(api_client, user1, user2, generated_document):
    u1, h1 = user1
    u2, h2 = user2
    doc_id = generated_document["id"]
    # Switch to user2
    as_user(u2)
    response = api_client.put(
        f"/api/v1/documents/{doc_id}",
        json={"content": "Hacked content"},
        headers=h2
    )
    assert response.status_code == 404


def test_delete_document(api_client, user1, ai_system):
    u1, h1 = user1
    as_user(u1)
    create_resp = api_client.post(
        "/api/v1/documents/generate",
        json={"ai_system_id": ai_system, "document_type": "technical_documentation"},
        headers=h1
    )
    doc_id = create_resp.json()["id"]
    delete_resp = api_client.delete(f"/api/v1/documents/{doc_id}", headers=h1)
    assert delete_resp.status_code == 204
    get_resp = api_client.get(f"/api/v1/documents/{doc_id}", headers=h1)
    assert get_resp.status_code == 404


def test_delete_document_wrong_user(api_client, user1, user2, generated_document):
    u1, h1 = user1
    u2, h2 = user2
    doc_id = generated_document["id"]
    # Switch to user2
    as_user(u2)
    response = api_client.delete(f"/api/v1/documents/{doc_id}", headers=h2)
    assert response.status_code == 404


def test_list_documents_requires_auth(api_client, shared_session):
    app.dependency_overrides.pop(get_current_user, None)
    response = api_client.get("/api/v1/documents/")
    assert response.status_code == 401