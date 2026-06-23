"""Unit tests for backend/app/modules/explainer/engine.py."""

from __future__ import annotations

import pytest
from unittest.mock import MagicMock, patch

from app.modules.explainer.engine import (
    _normalize,
    _extract_keywords,
    _match_factors,
    _build_questionnaire,
    _compute_confidence,
    explain_risk,
    FACTOR_KEYWORDS,
    ARTICLE_LIBRARY,
)
from app.schemas.explain import ExplainRequest, ExplainResponse


class TestNormalize:
    """Tests for _normalize()."""

    def test_lowercases_text(self) -> None:
        assert _normalize("HELLO World") == "hello world"

    def test_strips_whitespace(self) -> None:
        assert _normalize("  hello  ") == "hello"


class TestExtractKeywords:
    """Tests for _extract_keywords()."""

    def test_removes_stop_words(self) -> None:
        """Common stop words should be filtered out."""
        result = _extract_keywords("the quick brown fox")
        assert "the" not in result
        assert "quick" in result

    def test_keeps_meaningful_terms(self) -> None:
        """Relevant compliance keywords should be preserved."""
        result = _extract_keywords(
            "AI system used for job candidate screening and recruitment"
        )
        assert "recruit" in result or "screening" in result or "hiring" in result

    def test_minimum_word_length(self) -> None:
        """Words shorter than 3 chars are excluded."""
        result = _extract_keywords("AI tool for HR use")
        assert all(len(w) >= 3 for w in result)


class TestMatchFactors:
    """Tests for _match_factors()."""

    def test_matches_hr_recruitment_keywords(self) -> None:
        result = _match_factors(
            "This AI system screens job applications and ranks candidates"
        )
        factor_ids = [fid for fid, _ in result]
        assert "hr_recruitment_screening" in factor_ids

    def test_matches_biometric_keywords(self) -> None:
        result = _match_factors(
            "Facial recognition system for employee identification"
        )
        factor_ids = [fid for fid, _ in result]
        assert "uses_biometric_data" in factor_ids

    def test_matches_law_enforcement_keywords(self) -> None:
        result = _match_factors(
            "Crime prediction algorithm for police surveillance"
        )
        factor_ids = [fid for fid, _ in result]
        assert "law_enforcement" in factor_ids

    def test_no_matches_returns_empty_list(self) -> None:
        result = _match_factors("A simple weather forecast application")
        assert result == []

    def test_returns_matched_keywords_with_factor(self) -> None:
        result = _match_factors("AI for biometric identity verification")
        for fid, keywords in result:
            if fid == "uses_biometric_data":
                assert any("biometric" in kw for kw in keywords)
                break


class TestBuildQuestionnaire:
    """Tests for _build_questionnaire()."""

    def test_all_factors_default_to_false(self) -> None:
        questionnaire = _build_questionnaire([])
        assert questionnaire.use_case_category == "other"
        assert questionnaire.is_safety_component is False
        assert questionnaire.affects_fundamental_rights is False

    def test_hr_recruitment_set_true_when_in_list(self) -> None:
        questionnaire = _build_questionnaire(["hr_recruitment_screening"])
        assert questionnaire.hr_recruitment_screening is True

    def test_multiple_factors_set_true(self) -> None:
        questionnaire = _build_questionnaire(
            ["hr_recruitment_screening", "uses_biometric_data"]
        )
        assert questionnaire.hr_recruitment_screening is True
        assert questionnaire.uses_biometric_data is True
        assert questionnaire.credit_worthiness is False


class TestComputeConfidence:
    """Tests for _compute_confidence()."""

    def test_no_matches_returns_075(self) -> None:
        from app.models.ai_system import RiskLevel
        result = _compute_confidence([], RiskLevel.MINIMAL)
        assert result == 0.75

    def test_single_keyword_returns_base_confidence(self) -> None:
        from app.models.ai_system import RiskLevel
        matched = [("hr_recruitment_screening", ["recruit"])]
        result = _compute_confidence(matched, RiskLevel.HIGH)
        assert 0.70 <= result <= 0.78

    def test_many_keywords_returns_high_confidence(self) -> None:
        from app.models.ai_system import RiskLevel
        matched = [
            ("hr_recruitment_screening", ["recruit", "screening", "hiring", "cv", "applicant", "ranking"]),
            ("uses_biometric_data", ["fingerprint", "biometric"]),
            ("makes_automated_decisions", ["automated", "decision"]),
        ]
        result = _compute_confidence(matched, RiskLevel.HIGH)
        assert result >= 0.90


class TestExplainRisk:
    """Tests for explain_risk()."""

    @patch("app.modules.explainer.engine.classify_risk")
    def test_returns_explain_response_with_matched_factors(
        self, mock_classify: MagicMock
    ) -> None:
        from app.models.ai_system import RiskLevel
        from app.schemas.ai_system import RiskClassificationRequest, RiskClassificationResponse

        mock_classify.return_value = RiskClassificationResponse(
            risk_level=RiskLevel.HIGH,
            use_case_category="employment",
            is_safety_component=False,
            affects_fundamental_rights=True,
            uses_biometric_data=False,
            makes_automated_decisions=True,
            hr_recruitment_screening=True,
            hr_promotion_termination=False,
            credit_worthiness=False,
            insurance_risk_assessment=False,
            law_enforcement=False,
            border_control=False,
            justice_system=False,
            interacts_with_humans=False,
            generates_synthetic_content=False,
            emotion_recognition=False,
            biometric_categorization=False,
            reasons=["High-risk recruitment AI"],
            requirements=["Conformity assessment required"],
        )

        request = ExplainRequest(
            description="AI system for job candidate screening and automated ranking without human review"
        )
        result = explain_risk(request)

        assert isinstance(result, ExplainResponse)
        assert result.risk_level == RiskLevel.HIGH
        assert 0 < result.confidence <= 1.0
        assert len(result.triggered_factors) > 0
        assert result.triggered_keywords  # keywords were extracted
        assert result.relevant_articles   # articles were matched
        mock_classify.assert_called_once()

    @patch("app.modules.explainer.engine.classify_risk")
    def test_empty_description_returns_minimal_risk(
        self, mock_classify: MagicMock
    ) -> None:
        from app.models.ai_system import RiskLevel
        from app.schemas.ai_system import RiskClassificationRequest, RiskClassificationResponse

        mock_classify.return_value = RiskClassificationResponse(
            risk_level=RiskLevel.MINIMAL,
            use_case_category="other",
            is_safety_component=False,
            affects_fundamental_rights=False,
            uses_biometric_data=False,
            makes_automated_decisions=False,
            hr_recruitment_screening=False,
            hr_promotion_termination=False,
            credit_worthiness=False,
            insurance_risk_assessment=False,
            law_enforcement=False,
            border_control=False,
            justice_system=False,
            interacts_with_humans=False,
            generates_synthetic_content=False,
            emotion_recognition=False,
            biometric_categorization=False,
            reasons=[],
            requirements=[],
        )

        request = ExplainRequest(description="Simple web page")
        result = explain_risk(request)
        assert result.risk_level == RiskLevel.MINIMAL
        assert result.confidence == 0.75  # no matches
