# backend/tests/test_document_share.py

import pytest
from jose import jwt
from datetime import datetime, timedelta
from app.core.config import settings
from app.models.user import User
from app.models.document import Document, DocumentType, DocumentStatus
from app.core.security import get_password_hash


@pytest.fixture
def test_user(client):
    """Register and return a test user with auth token."""
    response = client.post("/api/v1/auth/register", json={
        "email": "test@example.com",
        "password": "Test1234",
        "full_name": "Test User",
        "company_name": "Test Corp"
    })
    assert response.status_code == 201
    
    login = client.post("/api/v1/auth/login", data={
        "username": "test@example.com",
        "password": "Test1234"
    })
    token = login.json()["access_token"]
    return {"headers": {"Authorization": f"Bearer {token}"}}


@pytest.fixture
def test_document(client, test_user):
    """Create and return a test document."""
    response = client.post("/api/v1/documents/", json={
        "title": "Test Document",
        "document_type": "technical_documentation",
        "content": "Test content"
    }, headers=test_user["headers"])
    assert response.status_code == 201
    return response.json()


# ── Tests ──────────────────────────────────────────────────────────────────

def test_create_share_link(client, test_user, test_document):
    response = client.post(
        f"/api/v1/documents/{test_document['id']}/share",
        headers=test_user["headers"]
    )
    assert response.status_code == 200
    data = response.json()
    assert "share_token" in data
    assert "expires_at" in data
    assert "share_url" in data


def test_access_shared_document_no_auth(client, test_user, test_document):
    """Should work without any auth header."""
    share = client.post(
        f"/api/v1/documents/{test_document['id']}/share",
        headers=test_user["headers"]
    )
    token = share.json()["share_token"]

    response = client.get(f"/api/v1/documents/share/{token}")
    assert response.status_code == 200
    assert response.json()["id"] == test_document["id"]


def test_expired_token_rejected(client):
    expired_token = jwt.encode(
        {
            "document_id": 1,
            "exp": datetime.utcnow() - timedelta(days=1),
            "type": "document_share"
        },
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    response = client.get(f"/api/v1/documents/share/{expired_token}")
    assert response.status_code == 401


def test_wrong_token_type_rejected(client):
    bad_token = jwt.encode(
        {
            "document_id": 1,
            "exp": datetime.utcnow() + timedelta(days=1),
            "type": "auth"
        },
        settings.SECRET_KEY,
        algorithm="HS256"
    )
    response = client.get(f"/api/v1/documents/share/{bad_token}")
    assert response.status_code == 400


def test_share_nonexistent_document(client, test_user):
    response = client.post(
        "/api/v1/documents/99999/share",
        headers=test_user["headers"]
    )
    assert response.status_code == 404


def test_share_other_users_document_denied(client, test_user, test_document):
    """User2 should not be able to share User1's document."""
    client.post("/api/v1/auth/register", json={
        "email": "user2@example.com",
        "password": "Test1234",
        "full_name": "User Two",
        "company_name": "Corp2"
    })
    login2 = client.post("/api/v1/auth/login", data={
        "username": "user2@example.com",
        "password": "Test1234"
    })
    token2 = login2.json()["access_token"]

    response = client.post(
        f"/api/v1/documents/{test_document['id']}/share",
        headers={"Authorization": f"Bearer {token2}"}
    )
    assert response.status_code == 404