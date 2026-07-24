"""
Unit tests for backend/app/modules/llm/document_generator.py —
generate_compliance_narrative function.

Tests cover:
  - FileNotFoundError from load_vector_store uses the fallback rag_context
  - Successful vector_store.load returns retrieved chunks as rag_context
  - LLMClient.call is invoked with the correct prompt arguments
  - Return value is a non-empty string
  - risk_assessment None is handled gracefully
"""

import pytest
from unittest.mock import patch, MagicMock

from app.models.ai_system import AISystem, RiskLevel, ComplianceStatus
from app.models.document import DocumentType
from app.modules.llm.document_generator import generate_compliance_narrative


class TestGenerateComplianceNarrative:
    @pytest.fixture
    def ai_system(self):
        """Minimal AI System fixture for testing."""
        system = MagicMock(spec=AISystem)
        system.name = "TestAI"
        system.version = "1.0"
        system.use_case = "Medical diagnosis"
        system.sector = "Healthcare"
        system.risk_level = RiskLevel.HIGH
        system.description = "A test AI system for compliance testing"
        return system

    def test_file_not_found_uses_fallback_context(self, ai_system):
        """When load_vector_store raises FileNotFoundError the function
        continues with the fallback rag_context string without raising."""

        with patch(
            "app.modules.llm.document_generator.load_vector_store",
            side_effect=FileNotFoundError("No FAISS index found"),
        ), patch(
            "app.modules.llm.document_generator.LLMClient"
        ) as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm.call.return_value = "Generated compliance narrative text"
            mock_llm_cls.return_value = mock_llm

            result = generate_compliance_narrative(
                document_type=DocumentType.RISK_ASSESSMENT,
                ai_system=ai_system,
                risk_assessment=None,
                company_name="TestCorp",
                user_id=None,
            )

            assert isinstance(result, str)
            assert len(result) > 0
            # Verify the LLM was still called despite the FileNotFoundError
            mock_llm.call.assert_called_once()
            # Verify the fallback context was used in the prompt
            call_kwargs = mock_llm.call.call_args
            prompt = call_kwargs.kwargs.get("prompt", "") if call_kwargs.kwargs else ""
            assert "No specific regulation context available" in prompt

    def test_successful_vector_store_provides_context(self, ai_system):
        """When load_vector_store succeeds, retrieved chunks are used as rag_context."""

        mock_doc = MagicMock()
        mock_doc.page_content = "Article 9 EU AI Act: Risk management shall be..."

        with patch(
            "app.modules.llm.document_generator.load_vector_store"
        ) as mock_load, patch(
            "app.modules.llm.document_generator.LLMClient"
        ) as mock_llm_cls:
            mock_vs = MagicMock()
            mock_vs.similarity_search.return_value = [mock_doc]
            mock_load.return_value = mock_vs

            mock_llm = MagicMock()
            mock_llm.call.return_value = "Generated document"
            mock_llm_cls.return_value = mock_llm

            result = generate_compliance_narrative(
                document_type=DocumentType.TECHNICAL_DOCUMENTATION,
                ai_system=ai_system,
                risk_assessment=None,
                company_name="TestCorp",
                user_id=1,
            )

            mock_vs.similarity_search.assert_called_once()
            # Verify the retrieved context appears in the prompt
            call_kwargs = mock_llm.call.call_args
            prompt = call_kwargs.kwargs.get("prompt", "") if call_kwargs.kwargs else ""
            assert "Article 9 EU AI Act" in prompt

    def test_llm_client_invoked_with_system_context(self, ai_system):
        """LLMClient.call is invoked with a prompt containing the system name,
        company name, and document type."""

        with patch(
            "app.modules.llm.document_generator.load_vector_store",
            side_effect=FileNotFoundError("no index"),
        ), patch(
            "app.modules.llm.document_generator.LLMClient"
        ) as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm.call.return_value = "Narrative output"
            mock_llm_cls.return_value = mock_llm

            generate_compliance_narrative(
                document_type=DocumentType.TRANSPARENCY_NOTICE,
                ai_system=ai_system,
                risk_assessment=None,
                company_name="AcmeAI Ltd",
                user_id=None,
            )

            call_kwargs = mock_llm.call.call_args
            prompt = call_kwargs.kwargs.get("prompt", "") if call_kwargs.kwargs else ""
            assert "TestAI" in prompt
            assert "AcmeAI Ltd" in prompt
            assert "transparency" in prompt.lower()

    def test_return_value_is_non_empty_string(self, ai_system):
        """The function must return a string with content, not None or empty."""

        with patch(
            "app.modules.llm.document_generator.load_vector_store",
            side_effect=FileNotFoundError("no index"),
        ), patch(
            "app.modules.llm.document_generator.LLMClient"
        ) as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm.call.return_value = "A compliance document was generated successfully."
            mock_llm_cls.return_value = mock_llm

            result = generate_compliance_narrative(
                document_type=DocumentType.RISK_ASSESSMENT,
                ai_system=ai_system,
                risk_assessment=None,
                company_name="TestCorp",
                user_id=None,
            )

            assert isinstance(result, str)
            assert len(result) > 0

    def test_risk_assessment_none_handled_gracefully(self, ai_system):
        """Passing risk_assessment=None must not raise — None values are
        handled in the function body and produce a 'None available' placeholder."""

        with patch(
            "app.modules.llm.document_generator.load_vector_store",
            side_effect=FileNotFoundError("no index"),
        ), patch(
            "app.modules.llm.document_generator.LLMClient"
        ) as mock_llm_cls:
            mock_llm = MagicMock()
            mock_llm.call.return_value = "Document without risk assessment"
            mock_llm_cls.return_value = mock_llm

            # Must not raise
            result = generate_compliance_narrative(
                document_type=DocumentType.HUMAN_OVERSIGHT_PLAN,
                ai_system=ai_system,
                risk_assessment=None,
                company_name="TestCorp",
                user_id=None,
            )

            assert isinstance(result, str)
            # Verify the fallback risk_assessment_details string was used
            call_kwargs = mock_llm.call.call_args
            prompt = call_kwargs.kwargs.get("prompt", "") if call_kwargs.kwargs else ""
            assert "None available" in prompt
