import json
from unittest.mock import MagicMock, patch

from app.modules.llm.llm_client import LLMClient
from app.schemas.llm_outputs import (
    ConformityDeclarationOutput,
    RiskAssessmentOutput,
    TechnicalDocumentationOutput,
)


def _response(content: dict | str):
    mock_response = MagicMock()
    mock_response.choices[0].message.content = (
        json.dumps(content) if isinstance(content, dict) else content
    )
    return mock_response


def _tech_doc_payload():
    return {
        "document_type": "technical_documentation",
        "system_name": "Hiring AI",
        "provider_name": "Aegis",
        "version": "1.0",
        "intended_purpose": "Rank candidates for recruiter review.",
        "system_description": "A model-assisted hiring workflow.",
        "system_architecture": "API, model service, audit store.",
        "input_data": "Candidate resumes and job criteria.",
        "output_specification": "Ranked candidate list with explanations.",
        "training_data": "Historical hiring records and validation sets.",
        "validation_testing": "Bias, accuracy, and robustness tests.",
        "performance_metrics": "Precision, recall, calibration, and drift.",
        "risk_management": [
            {
                "risk": "Biased ranking",
                "severity": "high",
                "likelihood": "medium",
                "mitigation": "Bias testing and human review.",
                "residual_risk": "medium",
            }
        ],
        "human_oversight": "Recruiters approve final decisions.",
        "logging_monitoring": "Inputs, outputs, and overrides are logged.",
        "cybersecurity": "Access control and vulnerability management.",
        "lifecycle_management": "Periodic review and change control.",
    }


def _risk_payload():
    return {
        "document_type": "risk_assessment",
        "system_name": "Hiring AI",
        "provider_name": "Aegis",
        "intended_purpose": "Rank candidates for recruiter review.",
        "risk_classification": "high",
        "classification_rationale": "Employment-related AI can affect access to work.",
        "foreseeable_misuse": ["Automated rejection without human review."],
        "identified_risks": [
            {
                "risk": "Discrimination",
                "severity": "high",
                "likelihood": "medium",
                "mitigation": "Representative validation and appeals.",
                "residual_risk": "medium",
            }
        ],
        "data_governance_risks": ["Incomplete training data."],
        "transparency_risks": ["Users may not understand ranking factors."],
        "human_oversight_risks": ["Reviewer over-reliance."],
        "robustness_cybersecurity_risks": ["Prompt injection in uploaded text."],
        "overall_residual_risk": "medium",
        "monitoring_plan": "Monthly drift and incident review.",
    }


def _conformity_payload():
    return {
        "document_type": "conformity_declaration",
        "system_name": "Hiring AI",
        "provider_name": "Aegis",
        "provider_address": "Not specified",
        "version": "1.0",
        "intended_purpose": "Rank candidates for recruiter review.",
        "risk_classification": "high",
        "applicable_regulation": "Regulation (EU) 2024/1689",
        "harmonised_standards": ["Not specified"],
        "conformity_assessment_procedure": "Internal control.",
        "requirements": [
            {
                "requirement": "Article 14 human oversight",
                "evidence": "Documented review workflow.",
                "status": "addressed",
            }
        ],
        "declaration_statement": "The provider declares conformity based on available evidence.",
        "signatory_name": "Not specified",
        "signatory_title": "Not specified",
        "place_and_date": "Not specified",
    }


def _client_with_mock(mock_client, supports_json_schema=True):
    with patch("app.modules.llm.llm_client.settings") as mock_settings:
        mock_settings.LLM_API_KEY = "test-key"
        mock_settings.LLM_BASE_URL = None
        mock_settings.LLM_MODEL = "gpt-4o-mini"
        mock_settings.LLM_TIMEOUT = 30.0
        mock_settings.LLM_SUPPORTS_JSON_SCHEMA = supports_json_schema
        with patch("app.modules.llm.llm_client.OpenAI", return_value=mock_client):
            with patch("app.modules.llm.llm_client.AsyncOpenAI"):
                return LLMClient(api_key="test-key")


def test_generate_structured_uses_json_schema_response_format():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _response(_tech_doc_payload())
    client = _client_with_mock(mock_client, supports_json_schema=True)

    result = client.generate_structured(
        messages=[{"role": "user", "content": "Generate technical documentation"}],
        output_schema=TechnicalDocumentationOutput,
        max_retries=1,
    )

    assert result["intended_purpose"] == "Rank candidates for recruiter review."
    call_kwargs = mock_client.chat.completions.create.call_args.kwargs
    assert call_kwargs["response_format"]["type"] == "json_schema"
    assert call_kwargs["response_format"]["json_schema"]["strict"] is True


def test_generate_structured_fallback_accepts_json_markdown_fence():
    mock_client = MagicMock()
    mock_client.chat.completions.create.return_value = _response(
        f"```json\n{json.dumps(_risk_payload())}\n```"
    )
    client = _client_with_mock(mock_client, supports_json_schema=False)

    result = client.generate_structured(
        messages=[{"role": "user", "content": "Generate risk assessment"}],
        output_schema=RiskAssessmentOutput,
        max_retries=1,
    )

    assert result["document_type"] == "risk_assessment"
    assert "response_format" not in mock_client.chat.completions.create.call_args.kwargs


def test_generate_structured_retries_after_validation_failure():
    invalid_payload = _conformity_payload()
    invalid_payload.pop("intended_purpose")

    mock_client = MagicMock()
    mock_client.chat.completions.create.side_effect = [
        _response(invalid_payload),
        _response(_conformity_payload()),
    ]
    client = _client_with_mock(mock_client, supports_json_schema=False)

    result = client.generate_structured(
        messages=[{"role": "user", "content": "Generate declaration"}],
        output_schema=ConformityDeclarationOutput,
        max_retries=2,
    )

    assert result["intended_purpose"] == "Rank candidates for recruiter review."
    assert mock_client.chat.completions.create.call_count == 2
    second_messages = mock_client.chat.completions.create.call_args.kwargs["messages"]
    assert "failed JSON schema validation" in second_messages[-1]["content"]
