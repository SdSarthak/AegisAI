"""Unit tests for document generation — all 3 template types."""

import pytest
from app.core.security import create_access_token


def get_auth_headers(user_id: int) -> dict:
    token = create_access_token(data={"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client, email, password="testpassword123"):
    client.post("/api/v1/auth/register", json={"email": email, "password": password})
    response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_ai_system(client, headers):
    response = client.post(
        "/api/v1/ai-systems/",
        json={"name": "Test AI System", "description": "A test system"},
        headers=headers
    )
    return response.json()["id"]


# ✅ Test 1: Generate Technical Documentation → 201
def test_generate_technical_documentation(client):
    headers = register_and_login(client, "tech_doc@example.com")
    system_id = create_ai_system(client, headers)

    response = client.post(
        "/api/v1/documents/generate",
        json={
            "ai_system_id": system_id,
            "document_type": "technical_documentation"
        },
        headers=headers
    )

    assert response.status_code == 201
    assert response.json() is not None


# ✅ Test 2: Generate Risk Assessment → 201
def test_generate_risk_assessment(client):
    headers = register_and_login(client, "risk@example.com")
    system_id = create_ai_system(client, headers)

    response = client.post(
        "/api/v1/documents/generate",
        json={
            "ai_system_id": system_id,
            "document_type": "risk_assessment"
        },
        headers=headers
    )

    assert response.status_code == 201
    assert response.json() is not None


# ✅ Test 3: Generate Conformity Declaration → 201
def test_generate_conformity_declaration(client):
    headers = register_and_login(client, "conformity@example.com")
    system_id = create_ai_system(client, headers)

    response = client.post(
        "/api/v1/documents/generate",
        json={
            "ai_system_id": system_id,
            "document_type": "conformity_declaration"
        },
        headers=headers
    )

    assert response.status_code == 201
    assert response.json() is not None


# ❌ Test 4: Non-existent system → 404
def test_generate_for_nonexistent_system(client):
    headers = register_and_login(client, "notsystem@example.com")

    response = client.post(
        "/api/v1/documents/generate",
        json={
            "ai_system_id": 99999,
            "document_type": "technical_documentation"
        },
        headers=headers
    )

    assert response.status_code == 404


# ❌ Test 5: Another user's system → 404
def test_generate_for_another_users_system(client):
    # User 1 creates a system
    headers_user1 = register_and_login(client, "user1@example.com")
    system_id = create_ai_system(client, headers_user1)

    # User 2 tries to generate doc for User 1's system
    headers_user2 = register_and_login(client, "user2@example.com")
    response = client.post(
        "/api/v1/documents/generate",
        json={
            "ai_system_id": system_id,
            "document_type": "technical_documentation"
        },
        headers=headers_user2
    )

    assert response.status_code == 404