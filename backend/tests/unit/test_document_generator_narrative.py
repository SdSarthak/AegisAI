"""
Unit tests for generate_compliance_narrative in app/modules/llm/document_generator.py.

Tests cover: RAG fallback on missing vector store, risk assessment details
in prompt, and None risk_assessment handling.
"""

import os
from unittest.mock import patch, MagicMock

# Set required env vars before any app imports
os.environ.setdefault("DATABASE_URL", "postgresql://user:pass@localhost/test")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-unit-tests-only")
os.environ.setdefault("VITE_API_BASE_URL", "http://localhost:8000")


class TestGenerateComplianceNarrative:
    """Tests for generate_compliance_narrative function."""

    def test_generates_fallback_rag_context_on_missing_vector_store(self):
        """When the vector store is absent (FileNotFoundError), a fallback rag_context is used."""
        from app.modules.llm.document_generator import generate_compliance_narrative
        import enum

        # Use a standalone enum for the test (avoids triggering app.models import chain)
        class DocumentType(str, enum.Enum):
            TECHNICAL_DOCUMENTATION = "technical_documentation"
            RISK_ASSESSMENT = "risk_assessment"
            CONFORMITY_DECLARATION = "conformity_declaration"

        mock_ai_system = MagicMock()
        mock_ai_system.name = "Test System"
        mock_ai_system.version = "1.0"
        mock_ai_system.use_case = "Medical diagnosis"
        mock_ai_system.sector = "Healthcare"
        mock_ai_system.risk_level = MagicMock(value="LIMITED")
        mock_ai_system.description = "A medical AI system"

        mock_risk_assessment = MagicMock()
        mock_risk_assessment.risk_level = MagicMock(value="LIMITED")
        mock_risk_assessment.findings = "No major issues found"
        mock_risk_assessment.recommendations = "Continue monitoring"

        mock_llm_client = MagicMock()
        mock_llm_client.call.return_value = "Generated compliance narrative."

        with (
            patch(
                "app.modules.llm.document_generator.load_vector_store",
                side_effect=FileNotFoundError("No index found"),
            ),
            patch(
                "app.modules.llm.document_generator.LLMClient",
                return_value=mock_llm_client,
            ),
        ):
            doc_type = DocumentType.TECHNICAL_DOCUMENTATION
            result = generate_compliance_narrative(
                document_type=doc_type,
                ai_system=mock_ai_system,
                risk_assessment=mock_risk_assessment,
                company_name="TestCorp",
                user_id=1,
            )

        assert result == "Generated compliance narrative."
        mock_llm_client.call.assert_called_once()
        call_kwargs = mock_llm_client.call.call_args[1]
        prompt = call_kwargs["prompt"]
        assert "Test System" in prompt
        assert "TestCorp" in prompt
        assert "No specific regulation context available" in prompt

    def test_includes_risk_assessment_details_in_prompt(self):
        """Risk assessment details should be included in the LLM prompt when provided."""
        from app.modules.llm.document_generator import generate_compliance_narrative
        import enum

        class DocumentType(str, enum.Enum):
            TECHNICAL_DOCUMENTATION = "technical_documentation"
            RISK_ASSESSMENT = "risk_assessment"
            CONFORMITY_DECLARATION = "conformity_declaration"

        mock_ai_system = MagicMock()
        mock_ai_system.name = "Risk System"
        mock_ai_system.version = "2.0"
        mock_ai_system.use_case = "Credit scoring"
        mock_ai_system.sector = "Finance"
        mock_ai_system.risk_level = MagicMock(value="HIGH")
        mock_ai_system.description = "Credit scoring system"

        mock_risk_assessment = MagicMock()
        mock_risk_assessment.risk_level = MagicMock(value="HIGH")
        mock_risk_assessment.findings = "Biased training data"
        mock_risk_assessment.recommendations = "Use balanced dataset"

        mock_vector_store = MagicMock()
        mock_vector_store.similarity_search.return_value = []

        mock_llm_client = MagicMock()
        mock_llm_client.call.return_value = "Narrative."

        with (
            patch(
                "app.modules.llm.document_generator.load_vector_store",
                return_value=mock_vector_store,
            ),
            patch(
                "app.modules.llm.document_generator.LLMClient",
                return_value=mock_llm_client,
            ),
        ):
            doc_type = DocumentType.RISK_ASSESSMENT
            result = generate_compliance_narrative(
                document_type=doc_type,
                ai_system=mock_ai_system,
                risk_assessment=mock_risk_assessment,
                company_name="FinCorp",
                user_id=2,
            )

        assert result == "Narrative."
        mock_llm_client.call.assert_called_once()
        call_kwargs = mock_llm_client.call.call_args[1]
        prompt = call_kwargs["prompt"]
        assert "Biased training data" in prompt
        assert "Use balanced dataset" in prompt
        assert "Assessed Risk Level: HIGH" in prompt
        # Verify vector store was queried
        mock_vector_store.similarity_search.assert_called_once()

    def test_handles_none_risk_assessment_without_crash(self):
        """When risk_assessment is None, the function should not crash."""
        from app.modules.llm.document_generator import generate_compliance_narrative
        import enum

        class DocumentType(str, enum.Enum):
            TECHNICAL_DOCUMENTATION = "technical_documentation"
            RISK_ASSESSMENT = "risk_assessment"
            CONFORMITY_DECLARATION = "conformity_declaration"

        mock_ai_system = MagicMock()
        mock_ai_system.name = "New System"
        mock_ai_system.version = "1.0"
        mock_ai_system.use_case = "Chatbot"
        mock_ai_system.sector = "Retail"
        mock_ai_system.risk_level = MagicMock(value="MINIMAL")
        mock_ai_system.description = "Retail chatbot"

        mock_llm_client = MagicMock()
        mock_llm_client.call.return_value = "Narrative without assessment."

        with (
            patch(
                "app.modules.llm.document_generator.load_vector_store",
                side_effect=FileNotFoundError("No index"),
            ),
            patch(
                "app.modules.llm.document_generator.LLMClient",
                return_value=mock_llm_client,
            ),
        ):
            doc_type = DocumentType.CONFORMITY_DECLARATION
            result = generate_compliance_narrative(
                document_type=doc_type,
                ai_system=mock_ai_system,
                risk_assessment=None,
                company_name=None,
                user_id=None,
            )

        assert result == "Narrative without assessment."
        mock_llm_client.call.assert_called_once()
