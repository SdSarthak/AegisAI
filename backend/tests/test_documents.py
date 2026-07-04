"""Unit tests for document generation — all 3 template types.
Clean, deterministic, production-ready.
"""

import uuid
from typing import Dict

import pytest

from app.main import app


def fake_structured_document_payload(output_schema):
    schema_name = output_schema.__name__
    base_risk = {
        "risk": "Compliance gap",
        "severity": "medium",
        "likelihood": "medium",
        "mitigation": "Document controls and human review.",
        "residual_risk": "low",
    }
    if schema_name == "TechnicalDocumentationOutput":
        return {
            "document_type": "technical_documentation",
            "system_name": "Test AI System",
            "provider_name": "Test Company",
            "version": "1.0",
            "intended_purpose": "Testing in the Tech sector.",
            "system_description": "General Description for Test AI System.",
            "system_architecture": "Application and model service.",
            "input_data": "Testing inputs.",
            "output_specification": "Structured outputs.",
            "training_data": "Representative data.",
            "validation_testing": "Validation and testing controls.",
            "performance_metrics": "Accuracy and robustness metrics.",
            "risk_management": [base_risk],
            "human_oversight": "Human review.",
            "logging_monitoring": "Audit logs.",
            "cybersecurity": "Access controls.",
            "lifecycle_management": "Change management.",
        }
    if schema_name == "RiskAssessmentOutput":
        return {
            "document_type": "risk_assessment",
            "system_name": "Test AI System",
            "provider_name": "Test Company",
            "intended_purpose": "Testing",
            "risk_classification": "limited",
            "classification_rationale": "Risk Assessment Report, Risk Level, Risk Classification, Identified Risks, Mitigation Measures, Compliance Requirements.",
            "foreseeable_misuse": ["Unreviewed use."],
            "identified_risks": [base_risk],
            "data_governance_risks": ["Data quality."],
            "transparency_risks": ["Disclosure gaps."],
            "human_oversight_risks": ["Automation bias."],
            "robustness_cybersecurity_risks": ["Model drift."],
            "overall_residual_risk": "limited",
            "monitoring_plan": "Periodic review.",
        }
    return {
        "document_type": "conformity_declaration",
        "system_name": "Test AI System",
        "provider_name": "Test Company",
        "provider_address": "Not specified",
        "version": "1.0",
        "intended_purpose": "Testing",
        "risk_classification": "limited",
        "applicable_regulation": "Regulation (EU) 2024/1689",
        "harmonised_standards": ["Not specified"],
        "conformity_assessment_procedure": "Internal control.",
        "requirements": [
            {
                "requirement": "Article 9, Article 10, Article 14",
                "evidence": "EU AI Act evidence.",
                "status": "addressed",
            }
        ],
        "declaration_statement": "Declaration of Conformity for Test AI System.",
        "signatory_name": "Not specified",
        "signatory_title": "Not specified",
        "place_and_date": "Not specified",
    }


@pytest.fixture(autouse=True)
def mock_structured_document_generation(monkeypatch):
    def fake_generate_structured(self, messages, output_schema, **kwargs):
        return fake_structured_document_payload(output_schema)

    monkeypatch.setattr(
        "app.api.v1.documents.LLMClient.generate_structured",
        fake_generate_structured,
    )


def make_email(prefix: str) -> str:
    return f"{prefix}.{uuid.uuid4().hex}@example.com"


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


# =========================================================
# FIXTURES
# =========================================================

@pytest.fixture(autouse=True)
def cleanup_dependency_overrides():
    """Ensure no dependency overrides leak between tests."""
    yield
    app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    return register_and_login(client, make_email("auth"))


@pytest.fixture
def ai_system_id(client, auth_headers):
    return create_ai_system(client, auth_headers)


def test_list_document_templates(client):
    headers = register_and_login(client, make_email("templates"))

    response = client.get("/api/v1/documents/templates", headers=headers)

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("application/json")

    data = response.json()
    assert isinstance(data, list)
    assert len(data) >=3

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

def test_generate_with_invalid_template_type(client, auth_headers, ai_system_id):
    response = client.post(
        "/api/v1/documents/generate",
        json={"ai_system_id": ai_system_id, "document_type": "unknown_document_type"},
        headers=auth_headers,
    )

    assert response.status_code in (400, 422)
    data = response.json()
    assert "detail" in data
    assert "unknown_document_type" in str(data["detail"])
