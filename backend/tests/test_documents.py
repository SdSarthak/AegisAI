"""Unit tests for document generation — all 3 template types.
Clean, deterministic, production-ready.
"""

import uuid
from typing import Any, Dict

import pytest

from app.main import app


@pytest.fixture(autouse=True)
def cleanup_dependency_overrides():
    """Ensure no dependency overrides leak between tests."""
    yield
    app.dependency_overrides.clear()


def make_email(prefix: str) -> str:
    return f"{prefix}.{uuid.uuid4().hex}@example.com"


@pytest.fixture
def auth_headers(client):
    return register_and_login(client, make_email("auth"))


@pytest.fixture
def ai_system_id(client, auth_headers):
    return create_ai_system(client, auth_headers)


def register_and_login(client, email: str, password: str = "TestPass123!") -> Dict[str, str]:
    register_response = client.post(
        "/api/v1/auth/register",
        json={"email": email, "password": password},
    )
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    assert login_response.status_code == 200

    token = login_response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


def create_ai_system(client, headers: Dict[str, str]) -> int:
    response = client.post(
        "/api/v1/ai-systems/",
        json={"name": "Test AI System", "description": "A test system"},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json()["id"]


def generate_document(client, headers: Dict[str, str], system_id: int, document_type: str):
    return client.post(
        "/api/v1/documents/generate",
        json={"ai_system_id": system_id, "document_type": document_type},
        headers=headers,
    )


def test_list_document_templates(client):
    headers = register_and_login(client, make_email("templates"))

    response = client.get("/api/v1/documents/templates", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >= 3

    template_types = {template["type"] for template in data}
    assert {"technical_documentation", "risk_assessment", "conformity_declaration"}.issubset(
        template_types
    )

    for template in data:
        assert "type" in template
        assert "name" in template
        assert "description" in template
        assert template["name"]
        assert template["description"]


@pytest.mark.parametrize(
    "document_type",
    ["technical_documentation", "risk_assessment", "conformity_declaration"],
)
def test_generate_document_for_each_template(client, document_type):
    headers = register_and_login(client, make_email(document_type))
    system_id = create_ai_system(client, headers)

    response = generate_document(client, headers, system_id, document_type)

    assert response.status_code == 201
    data = response.json()
    assert data["document_type"] == document_type
    assert data["ai_system_id"] == system_id
    assert data["status"] == "generated"
    assert data["title"]
    assert data["content"]
    assert data["id"] is not None


@pytest.mark.parametrize("method", ["GET", "PUT", "DELETE", "PATCH"])
def test_generate_document_rejects_wrong_methods(client, method):
    response = client.request(method, "/api/v1/documents/generate")
    assert response.status_code == 405


def test_generate_for_nonexistent_system(client):
    headers = register_and_login(client, make_email("nonsystem"))

    response = client.post(
        "/api/v1/documents/generate",
        json={"ai_system_id": 99999, "document_type": "technical_documentation"},
        headers=headers,
    )

    assert response.status_code == 404


def test_generate_for_another_users_system(client):
    headers_user1 = register_and_login(client, make_email("user1"))
    system_id = create_ai_system(client, headers_user1)

    headers_user2 = register_and_login(client, make_email("user2"))
    response = client.post(
        "/api/v1/documents/generate",
        json={"ai_system_id": system_id, "document_type": "technical_documentation"},
        headers=headers_user2,
    )

    assert response.status_code == 404


def test_generate_with_invalid_template_type(client):
    headers = register_and_login(client, make_email("invalid-template"))
    system_id = create_ai_system(client, headers)

    response = client.post(
        "/api/v1/documents/generate",
        json={"ai_system_id": system_id, "document_type": "unknown_document_type"},
        headers=headers,
    )

    assert response.status_code == 400
    assert "unknown_document_type" in response.json()["detail"]
