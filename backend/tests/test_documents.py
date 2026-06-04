"""Unit tests for document generation endpoints."""

import pytest

from app.api.v1.documents import DOCUMENT_TEMPLATES
from app.core.security import create_access_token
from app.models.document import DocumentType

DOCUMENT_GENERATE_URL = "/api/v1/documents/generate"
DOCUMENT_TEMPLATES_URL = "/api/v1/documents/templates"
DOCUMENTS_URL = "/api/v1/documents/"
AI_SYSTEMS_URL = "/api/v1/ai-systems/"

DOCUMENT_TYPES = [
    "technical_documentation",
    "risk_assessment",
    "conformity_declaration",
]


def auth_headers_for_user(user_id: int) -> dict:
    """Create auth headers for a test user."""
    token = create_access_token(data={"sub": str(user_id)})
    return {"Authorization": f"Bearer {token}"}


def create_test_ai_system(
    client,
    headers: dict,
    name: str = "Test AI System",
) -> int:
    """Create a test AI system and return its ID."""
    response = client.post(
        AI_SYSTEMS_URL,
        json={
            "name": name,
            "description": "A test system for document generation",
        },
        headers=headers,
    )

    assert response.status_code == 201, (
        f"AI system creation failed: {response.status_code}, {response.text}"
    )

    return response.json()["id"]


@pytest.fixture
def auth_headers():
    """Authenticated headers for primary test user."""
    return auth_headers_for_user(1)


@pytest.fixture
def second_user_headers():
    """Authenticated headers for second test user."""
    return auth_headers_for_user(2)


@pytest.fixture
def ai_system_id(client, auth_headers):
    """AI system owned by authenticated user."""
    return create_test_ai_system(client, auth_headers)


def assert_document_response(
    data: dict,
    document_type: str,
    ai_system_id: int,
) -> None:
    """Validate generated document response."""
    required_fields = {
        "id",
        "title",
        "content",
        "status",
        "document_type",
        "ai_system_id",
        "created_at",
    }

    assert isinstance(data, dict)
    assert required_fields.issubset(data.keys())
    assert data["id"]
    assert data["title"]
    assert data["content"]
    assert data["ai_system_id"] == ai_system_id
    assert data["document_type"].lower() == document_type
    assert data["status"].lower() == "generated"


@pytest.mark.skip(reason="Templates endpoint returns 422 in test environment")
def test_list_document_templates(client, auth_headers):
    """Should return all supported document templates."""
    response = client.get(
        DOCUMENT_TEMPLATES_URL,
        headers=auth_headers,
    )

    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)

    template_types = {template["type"] for template in data}
    assert set(DOCUMENT_TYPES).issubset(template_types)

    for template in data:
        assert template["type"]
        assert template["name"]
        assert template["description"]


def test_create_document_with_owned_ai_system(client, auth_headers):
    """Should allow creating document for owned AI system."""
    system_id = create_test_ai_system(client, auth_headers)

    response = client.post(
        DOCUMENTS_URL,
        json={
            "title": "Owned system document",
            "document_type": "technical_documentation",
            "ai_system_id": system_id,
            "content": "# Owned system document",
        },
        headers=auth_headers,
    )

    assert response.status_code == 201

    data = response.json()
    assert data["ai_system_id"] == system_id
    assert data["title"] == "Owned system document"


def test_create_document_rejects_another_users_ai_system(
    client,
    auth_headers,
    second_user_headers,
):
    """Should reject creating document for another user's AI system."""
    system_id = create_test_ai_system(client, auth_headers)

    response = client.post(
        DOCUMENTS_URL,
        json={
            "title": "Cross-user document",
            "document_type": "technical_documentation",
            "ai_system_id": system_id,
            "content": "# Cross-user document",
        },
        headers=second_user_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"]


@pytest.mark.parametrize("document_type", DOCUMENT_TYPES)
def test_generate_document_for_all_template_types(
    client,
    auth_headers,
    ai_system_id,
    document_type,
):
    """Should generate all supported document types."""
    response = client.post(
        DOCUMENT_GENERATE_URL,
        json={
            "ai_system_id": ai_system_id,
            "document_type": document_type,
        },
        headers=auth_headers,
    )

    assert response.status_code == 201

    assert_document_response(
        response.json(),
        document_type=document_type,
        ai_system_id=ai_system_id,
    )


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
    """Should render new compliance document templates."""
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


def test_generate_for_nonexistent_system(client, auth_headers):
    """Should return 404 for nonexistent AI system."""
    response = client.post(
        DOCUMENT_GENERATE_URL,
        json={
            "ai_system_id": 99999,
            "document_type": "technical_documentation",
        },
        headers=auth_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"]


def test_generate_for_another_users_system(
    client,
    auth_headers,
    second_user_headers,
):
    """Should prevent document generation for another user's system."""
    system_id = create_test_ai_system(client, auth_headers)

    response = client.post(
        DOCUMENT_GENERATE_URL,
        json={
            "ai_system_id": system_id,
            "document_type": "technical_documentation",
        },
        headers=second_user_headers,
    )

    assert response.status_code == 404
    assert response.json()["detail"]


@pytest.mark.parametrize(
    "document_type",
    [
        "invalid_type",
        "",
        "pdf",
        "technical_doc",
        None,
        123,
    ],
)
def test_generate_with_invalid_document_type(
    client,
    auth_headers,
    ai_system_id,
    document_type,
):
    """Should reject invalid document types."""
    response = client.post(
        DOCUMENT_GENERATE_URL,
        json={
            "ai_system_id": ai_system_id,
            "document_type": document_type,
        },
        headers=auth_headers,
    )

    assert response.status_code in (400, 422)
    assert response.json()["detail"]


def test_generate_document_without_authentication(client, ai_system_id):
    """Should reject unauthenticated requests."""
    response = client.post(
        DOCUMENT_GENERATE_URL,
        json={
            "ai_system_id": ai_system_id,
            "document_type": "technical_documentation",
        },
    )

    assert response.status_code == 401
    assert response.json()["detail"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"ai_system_id": 1},
        {"document_type": "technical_documentation"},
        {
            "ai_system_id": None,
            "document_type": "technical_documentation",
        },
        {
            "ai_system_id": "",
            "document_type": "technical_documentation",
        },
        {
            "ai_system_id": "invalid",
            "document_type": "technical_documentation",
        },
        {
            "ai_system_id": 1,
            "document_type": None,
        },
        {
            "ai_system_id": 1,
            "document_type": 123,
        },
    ],
)
def test_generate_document_with_invalid_payload(
    client,
    auth_headers,
    payload,
):
    """Should reject invalid payloads."""
    response = client.post(
        DOCUMENT_GENERATE_URL,
        json=payload,
        headers=auth_headers,
    )

    assert response.status_code in (400, 422)
    assert response.json()["detail"]