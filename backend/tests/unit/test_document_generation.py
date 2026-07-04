"""Unit tests for document generation functionality.

Tests the generate_document endpoint with three template types:
- TECHNICAL_DOCUMENTATION
- RISK_ASSESSMENT
- CONFORMITY_DECLARATION
"""

import json
import os

os.environ.setdefault("SECRET_KEY", "test-secret-key")

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models.user import User, SubscriptionTier
from app.models.ai_system import AISystem, RiskLevel
from app.models.document import Document, DocumentType, DocumentStatus


def _fake_structured_document_payload(output_schema):
    base_risk = {
        "risk": "Compliance gap",
        "severity": "medium",
        "likelihood": "medium",
        "mitigation": "Document controls and human review.",
        "residual_risk": "low",
    }
    if output_schema.__name__ == "TechnicalDocumentationOutput":
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
    if output_schema.__name__ == "RiskAssessmentOutput":
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
        return _fake_structured_document_payload(output_schema)

    monkeypatch.setattr(
        "app.api.v1.documents.LLMClient.generate_structured",
        fake_generate_structured,
    )


def _content_text(content) -> str:
    return json.dumps(content) if isinstance(content, dict) else content


def _build_test_session_local(database_url: str):
    """Build a test database session."""
    engine = create_engine(database_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    return sessionmaker(autocommit=False, autoflush=False, bind=engine)


def _create_test_user(db):
    """Create a test user."""
    user = User(
        email="test@example.com",
        hashed_password="hashed_password",
        full_name="Test User",
        company_name="Test Company",
        subscription_tier=SubscriptionTier.FREE,
        is_active=True,
        is_verified=True,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _create_test_ai_system(db, owner_id: int):
    """Create a test AI system."""
    ai_system = AISystem(
        owner_id=owner_id,
        name="Test AI System",
        description="A test AI system for unit testing",
        version="1.0",
        use_case="Testing",
        sector="Tech",
        risk_level=RiskLevel.LIMITED,
    )
    db.add(ai_system)
    db.commit()
    db.refresh(ai_system)
    return ai_system


class TestDocumentGeneration:
    """Test suite for document generation."""

    def test_generate_technical_documentation(self, tmp_path):
        """Test generating a TECHNICAL_DOCUMENTATION template."""
        database_url = f"sqlite:///{tmp_path / 'test_tech_doc.db'}"
        testing_session_local = _build_test_session_local(database_url)

        def override_get_db():
            db = testing_session_local()
            try:
                yield db
            finally:
                db.close()

        db = testing_session_local()
        user = _create_test_user(db)
        ai_system = _create_test_ai_system(db, user.id)

        def override_current_user():
            return user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_current_user

        client = TestClient(app)
        response = client.post(
            "/api/v1/documents/generate",
            json={
                "document_type": "technical_documentation",
                "ai_system_id": ai_system.id,
            },
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert "title" in data
        assert "document_type" in data
        assert "content" in data
        assert "status" in data

        # Verify template type
        assert data["document_type"] == "technical_documentation"

        # Verify placeholder replacement in content
        content = _content_text(data["content"])
        assert "Test AI System" in content, "system_name not replaced"
        assert "1.0" in content, "version not replaced"
        assert "Testing" in content, "use_case not replaced"
        assert "Tech" in content, "sector not replaced"

        # Verify document title
        assert "Technical Documentation" in data["title"]

        # Verify generated status
        assert data["status"] == "generated"

        app.dependency_overrides.clear()

    def test_generate_risk_assessment(self, tmp_path):
        """Test generating a RISK_ASSESSMENT template."""
        database_url = f"sqlite:///{tmp_path / 'test_risk_assessment.db'}"
        testing_session_local = _build_test_session_local(database_url)

        def override_get_db():
            db = testing_session_local()
            try:
                yield db
            finally:
                db.close()

        db = testing_session_local()
        user = _create_test_user(db)
        ai_system = _create_test_ai_system(db, user.id)

        def override_current_user():
            return user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_current_user

        client = TestClient(app)
        response = client.post(
            "/api/v1/documents/generate",
            json={
                "document_type": "risk_assessment",
                "ai_system_id": ai_system.id,
            },
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert "title" in data
        assert "document_type" in data
        assert "content" in data

        # Verify template type
        assert data["document_type"] == "risk_assessment"

        # Verify placeholder replacement in content
        content = _content_text(data["content"])
        assert "Test AI System" in content, "system_name not replaced"
        assert "Testing" in content, "use_case not replaced"
        assert "limited" in content.lower(), "risk_level not replaced"

        # Verify document title
        assert "Risk Assessment" in data["title"]

        # Verify specific risk assessment sections exist
        assert "Risk Level" in content
        assert "Risk Classification" in content
        assert "Identified Risks" in content
        assert "Mitigation Measures" in content
        assert "Compliance Requirements" in content

        app.dependency_overrides.clear()

    def test_generate_conformity_declaration(self, tmp_path):
        """Test generating a CONFORMITY_DECLARATION template."""
        database_url = f"sqlite:///{tmp_path / 'test_conformity.db'}"
        testing_session_local = _build_test_session_local(database_url)

        def override_get_db():
            db = testing_session_local()
            try:
                yield db
            finally:
                db.close()

        db = testing_session_local()
        user = _create_test_user(db)
        ai_system = _create_test_ai_system(db, user.id)

        def override_current_user():
            return user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_current_user

        client = TestClient(app)
        response = client.post(
            "/api/v1/documents/generate",
            json={
                "document_type": "conformity_declaration",
                "ai_system_id": ai_system.id,
            },
        )

        assert response.status_code == 201, f"Expected 201, got {response.status_code}: {response.text}"
        data = response.json()

        # Verify response structure
        assert "id" in data
        assert "title" in data
        assert "document_type" in data
        assert "content" in data

        # Verify template type
        assert data["document_type"] == "conformity_declaration"

        # Verify placeholder replacement in content
        content = _content_text(data["content"])
        assert "Test AI System" in content, "system_name not replaced"
        assert "1.0" in content, "version not replaced"
        assert "Test Company" in content, "company_name not replaced"

        # Verify document title
        assert "Conformity Declaration" in data["title"]

        # Verify specific conformity declaration sections exist
        assert "Declaration of Conformity" in content
        assert "EU AI Act" in content
        assert "Article 9" in content  # Risk Management System
        assert "Article 10" in content  # Data Governance
        assert "Article 14" in content  # Human Oversight

        app.dependency_overrides.clear()

    def test_generate_document_invalid_ai_system(self, tmp_path):
        """Test document generation with non-existent AI system."""
        database_url = f"sqlite:///{tmp_path / 'test_invalid_ai.db'}"
        testing_session_local = _build_test_session_local(database_url)

        def override_get_db():
            db = testing_session_local()
            try:
                yield db
            finally:
                db.close()

        db = testing_session_local()
        user = _create_test_user(db)

        def override_current_user():
            return user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_current_user

        client = TestClient(app)
        response = client.post(
            "/api/v1/documents/generate",
            json={
                "document_type": "technical_documentation",
                "ai_system_id": 9999,  # Non-existent ID
            },
        )

        assert response.status_code == 404, f"Expected 404, got {response.status_code}"

        app.dependency_overrides.clear()

    def test_generate_document_invalid_type(self, tmp_path):
        """Test document generation with invalid document type."""
        database_url = f"sqlite:///{tmp_path / 'test_invalid_type.db'}"
        testing_session_local = _build_test_session_local(database_url)

        def override_get_db():
            db = testing_session_local()
            try:
                yield db
            finally:
                db.close()

        db = testing_session_local()
        user = _create_test_user(db)
        ai_system = _create_test_ai_system(db, user.id)

        def override_current_user():
            return user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_current_user

        client = TestClient(app)
        response = client.post(
            "/api/v1/documents/generate",
            json={
                "document_type": "invalid_type",
                "ai_system_id": ai_system.id,
            },
        )

        # FastAPI validation should catch this
        assert response.status_code == 422, f"Expected 422, got {response.status_code}"

        app.dependency_overrides.clear()

    def test_generate_all_three_template_types_content(self, tmp_path):
        """Test all three templates produce different content."""
        database_url = f"sqlite:///{tmp_path / 'test_all_templates.db'}"
        testing_session_local = _build_test_session_local(database_url)

        def override_get_db():
            db = testing_session_local()
            try:
                yield db
            finally:
                db.close()

        db = testing_session_local()
        user = _create_test_user(db)
        ai_system = _create_test_ai_system(db, user.id)

        def override_current_user():
            return user

        app.dependency_overrides[get_db] = override_get_db
        app.dependency_overrides[get_current_user] = override_current_user

        client = TestClient(app)

        # Generate all three template types
        template_types = [
            "technical_documentation",
            "risk_assessment",
            "conformity_declaration",
        ]

        contents = {}
        for doc_type in template_types:
            response = client.post(
                "/api/v1/documents/generate",
                json={
                    "document_type": doc_type,
                    "ai_system_id": ai_system.id,
                },
            )
            assert response.status_code == 201
            contents[doc_type] = _content_text(response.json()["content"])

        # Verify each template has unique content
        assert contents["technical_documentation"] != contents["risk_assessment"]
        assert contents["risk_assessment"] != contents["conformity_declaration"]
        assert contents["technical_documentation"] != contents["conformity_declaration"]

        # Verify specific markers for each template type
        assert "General Description" in contents["technical_documentation"]
        assert "Risk Assessment Report" in contents["risk_assessment"]
        assert "Declaration of Conformity" in contents["conformity_declaration"]

        app.dependency_overrides.clear()
