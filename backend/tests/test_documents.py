"""Unit tests for document generation — all 3 template types."""

import pytest


@pytest.fixture
def ai_system_id(client, auth_headers):
    response = client.post(
        "/api/v1/ai-systems/",
        json={"name": "Test AI System", "description": "A test system"},
        headers=auth_headers
    )
    return response.json()["id"]


def test_list_document_templates(client, auth_headers):
    response = client.get(
        "/api/v1/documents/templates",
        headers=auth_headers
    )

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3

    template_types = {template["type"] for template in data}
    assert "technical_documentation" in template_types
    assert "risk_assessment" in template_types
    assert "conformity_declaration" in template_types

    for template in data:
        assert "type" in template
        assert "name" in template
        assert "description" in template
        assert template["name"]
        assert template["description"]


def test_create_document_with_owned_ai_system(client, auth_headers, ai_system_id):
    response = client.post(
        "/api/v1/documents/",
        json={
            "title": "Owned system document",
            "document_type": "technical_documentation",
            "ai_system_id": ai_system_id,
            "content": "# Owned system document",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["ai_system_id"] == ai_system_id
    assert data["title"] == "Owned system document"


def test_create_document_rejects_another_users_ai_system(client, auth_headers, other_user_auth_headers):
    response = client.post(
        "/api/v1/ai-systems/",
        json={"name": "Test AI System", "description": "A test system"},
        headers=auth_headers
    )
    system_id = response.json()["id"]

    response = client.post(
        "/api/v1/documents/",
        json={
            "title": "Cross-user document",
            "document_type": "technical_documentation",
            "ai_system_id": system_id,
            "content": "# Cross-user document",
        },
        headers=other_user_auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "AI system not found"


@pytest.mark.parametrize("document_type", [
    "technical_documentation",
    "risk_assessment",
    "conformity_declaration",
])
def test_generate_document(client, auth_headers, ai_system_id, document_type):
    response = client.post(
        "/api/v1/documents/generate",
        json={
            "ai_system_id": ai_system_id,
            "document_type": document_type
        },
        headers=auth_headers
    )

    assert response.status_code == 201
    assert response.json() is not None


def test_generate_for_nonexistent_system(client, auth_headers):
    response = client.post(
        "/api/v1/documents/generate",
        json={
            "ai_system_id": 99999,
            "document_type": "technical_documentation"
        },
        headers=auth_headers
    )

    assert response.status_code == 404


def test_generate_for_another_users_system(client, auth_headers, other_user_auth_headers):
    response = client.post(
        "/api/v1/ai-systems/",
        json={"name": "Test AI System", "description": "A test system"},
        headers=auth_headers
    )
    system_id = response.json()["id"]

    response = client.post(
        "/api/v1/documents/generate",
        json={
            "ai_system_id": system_id,
            "document_type": "technical_documentation"
        },
        headers=other_user_auth_headers
    )

    assert response.status_code == 404


def test_generate_invalid_document_type(client, auth_headers, ai_system_id):
    response = client.post(
        "/api/v1/documents/generate",
        json={
            "ai_system_id": ai_system_id,
            "document_type": "invalid_document_type"
        },
        headers=auth_headers
    )

    assert response.status_code == 422


def test_generate_missing_auth(client, ai_system_id):
    response = client.post(
        "/api/v1/documents/generate",
        json={
            "ai_system_id": ai_system_id,
            "document_type": "technical_documentation"
        },
    )

    assert response.status_code == 401


def test_generate_invalid_payload(client, auth_headers):
    response = client.post(
        "/api/v1/documents/generate",
        json={},
        headers=auth_headers
    )

    assert response.status_code == 422
