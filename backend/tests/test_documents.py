"""Unit tests for document generation templates."""

import pytest
from app.core.security import create_access_token
from app.api.v1.documents import DOCUMENT_TEMPLATES
from app.models.document import DocumentType


def get_auth_headers(user_id: int) -> dict:
    token = create_access_token(data={"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


def register_and_login(client, email, password="TestPass123!"):
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

def test_list_document_templates(client):
    headers = get_auth_headers(user_id=1)

    response = client.get(
        "/api/v1/documents/templates",
        headers=headers
    )

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 5

    template_types = {template["type"] for template in data}
    assert "technical_documentation" in template_types
    assert "risk_assessment" in template_types
    assert "conformity_declaration" in template_types
    assert "data_governance" in template_types
    assert "transparency_notice" in template_types

    for template in data:
        assert "type" in template
        assert "name" in template
        assert "description" in template
        assert template["name"]
        assert template["description"]


def test_create_document_with_owned_ai_system(client):
    headers = register_and_login(client, "create_owned_doc@example.com")
    system_id = create_ai_system(client, headers)

    response = client.post(
        "/api/v1/documents/",
        json={
            "title": "Owned system document",
            "document_type": "technical_documentation",
            "ai_system_id": system_id,
            "content": "# Owned system document",
        },
        headers=headers,
    )

    assert response.status_code == 201
    data = response.json()
    assert data["ai_system_id"] == system_id
    assert data["title"] == "Owned system document"


def test_create_document_rejects_another_users_ai_system(client):
    headers_user1 = register_and_login(client, "doc_owner@example.com")
    system_id = create_ai_system(client, headers_user1)

    headers_user2 = register_and_login(client, "doc_attacker@example.com")
    response = client.post(
        "/api/v1/documents/",
        json={
            "title": "Cross-user document",
            "document_type": "technical_documentation",
            "ai_system_id": system_id,
            "content": "# Cross-user document",
        },
        headers=headers_user2,
    )

    assert response.status_code == 404
    assert response.json()["detail"] == "AI system not found"


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


@pytest.mark.parametrize(
    "document_type,expected_title,expected_content",
    [
        (
            "data_governance",
            "Data Governance",
            ["Article 10", "Data Quality Controls", "Data Provenance"],
        ),
        (
            "transparency_notice",
            "Transparency Notice",
            ["Article 50", "AI System Disclosure", "User Instructions"],
        ),
    ],
)
def test_generate_new_compliance_document_templates(
    document_type,
    expected_title,
    expected_content,
):
    template = DOCUMENT_TEMPLATES[DocumentType(document_type)]
    content = template.format(
        system_name="Test AI System",
        version="1.0",
        use_case="Testing",
        sector="Technology",
        description="A test AI system",
        risk_level="limited",
        date="2026-06-01",
        company_name="Test Company",
        classification_reasons="See risk assessment details",
        recommendations="Based on risk assessment",
        requirements="See applicable requirements above",
        next_steps="Complete all checklist items",
    )

    assert expected_title in content
    for section in expected_content:
        assert section in content


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
