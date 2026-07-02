"""
Unit tests for backend/app/modules/explainer/engine.py.

Tests cover:
  - _normalize(): case and whitespace normalization
  - _extract_keywords(): stop-word removal and min-length filter
  - _match_factors(): keyword pattern matching and factor triggering
  - _build_questionnaire(): RiskClassificationRequest construction
  - _compute_confidence(): confidence score based on keyword/factor counts
  - explain_risk(): full integration through the explainer pipeline
"""

import pytest
from unittest.mock import patch, MagicMock

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
from app.schemas.explain import ExplainRequest
from app.models.ai_system import RiskLevel


class TestNormalize:
    """Tests for _normalize()."""

    def test_lowercases_text(self):
        assert _normalize("HELLO WORLD") == "hello world"

    def test_strips_whitespace(self):
        assert _normalize("  hello  ") == "hello"

    def test_strips_newlines_and_tabs(self):
        # .strip() removes leading/trailing whitespace including newlines
        assert _normalize("  hello\n\tworld  ") == "hello\n\tworld"


class TestExtractKeywords:
    """Tests for _extract_keywords()."""

    def test_extracts_alpha_words(self):
        result = _extract_keywords("The AI system uses credit scoring for loans")
        assert "uses" in result
        assert "credit" in result
        assert "scoring" in result
        assert "loans" in result

    def test_removes_stop_words(self):
        result = _extract_keywords("The AI system for the company and its employees")
        assert "the" not in result
        assert "for" not in result
        assert "and" not in result
        assert "company" in result
        assert "employees" in result

    def test_filters_short_words_below_3_chars(self):
        result = _extract_keywords("a big application process")
        assert "a" not in result
        assert "big" in result
        assert "application" in result
        assert "process" in result

    def test_returns_empty_list_for_stop_words_only(self):
        result = _extract_keywords("the a an for to and or")
        assert result == []


class TestMatchFactors:
    """Tests for _match_factors()."""

    def test_matches_recruitment_keywords(self):
        result = _match_factors("The system screens CVs and ranks job applicants")
        factor_ids = [fid for fid, _ in result]
        assert "hr_recruitment_screening" in factor_ids

    def test_matches_credit_keywords(self):
        result = _match_factors("AI evaluates creditworthiness and loan eligibility")
        factor_ids = [fid for fid, _ in result]
        assert "credit_worthiness" in factor_ids

    def test_matches_biometric_keywords(self):
        result = _match_factors("Facial recognition identifies users by fingerprint")
        factor_ids = [fid for fid, _ in result]
        assert "uses_biometric_data" in factor_ids

    def test_matches_multiple_factors(self):
        result = _match_factors(
            "AI system screens CVs for recruitment and evaluates credit scores"
        )
        factor_ids = [fid for fid, _ in result]
        assert "hr_recruitment_screening" in factor_ids
        assert "credit_worthiness" in factor_ids

    def test_returns_empty_for_no_matches(self):
        result = _match_factors("AI generates images of cats")
        assert result == []

    def test_returns_matched_keywords_in_result(self):
        result = _match_factors("AI screens job candidates in recruitment")
        matched = dict(result)
        assert "recruit" in matched.get("hr_recruitment_screening", [])


class TestBuildQuestionnaire:
    """Tests for _build_questionnaire()."""

    def test_builds_questionnaire_with_no_factors(self):
        req = _build_questionnaire([])
        assert req.use_case_category == "other"
        assert req.is_safety_component is False
        assert req.uses_biometric_data is False

    def test_sets_matched_factors_to_true(self):
        req = _build_questionnaire(["hr_recruitment_screening", "credit_worthiness"])
        assert req.hr_recruitment_screening is True
        assert req.credit_worthiness is True
        assert req.is_safety_component is False

    def test_preserves_false_for_unmatched_factors(self):
        req = _build_questionnaire(["uses_biometric_data"])
        assert req.uses_biometric_data is True
        assert req.hr_recruitment_screening is False
        assert req.law_enforcement is False


class TestComputeConfidence:
    """Tests for _compute_confidence()."""

    def test_no_matches_returns_075(self):
        confidence = _compute_confidence([], RiskLevel.MINIMAL)
        assert confidence == 0.75

    def test_single_keyword_returns_low_confidence(self):
        matched = [("credit_worthiness", ["credit"])]
        confidence = _compute_confidence(matched, RiskLevel.HIGH)
        assert 0.70 <= confidence <= 0.78

    def test_many_keywords_returns_high_confidence(self):
        matched = [
            ("hr_recruitment_screening", ["recruit", "cv", "hiring", "job", "applicant"]),
            ("hr_promotion_termination", ["promot", "terminat", "fire"]),
            ("credit_worthiness", ["credit", "loan"]),
        ]
        confidence = _compute_confidence(matched, RiskLevel.HIGH)
        assert confidence >= 0.85

    def test_confidence_rounded_to_two_decimals(self):
        matched = [("credit_worthiness", ["credit"])]
        confidence = _compute_confidence(matched, RiskLevel.MINIMAL)
        assert round(confidence, 2) == confidence


class TestArticleLibrary:
    """Smoke tests for article library completeness."""

    def test_all_factor_keywords_have_article_entries(self):
        for factor_id in FACTOR_KEYWORDS:
            assert factor_id in ARTICLE_LIBRARY, f"Missing article for {factor_id}"

    def test_article_library_entries_have_required_fields(self):
        for factor_id, article in ARTICLE_LIBRARY.items():
            assert article.article, f"Missing article number for {factor_id}"
            assert article.title, f"Missing title for {factor_id}"
            assert article.summary, f"Missing summary for {factor_id}"


class TestExplainRisk:
    """Integration tests for explain_risk()."""

    def test_high_risk_description_returns_high_risk(self):
        with patch(
            "app.api.v1.classification.classify_risk",
            return_value=MagicMock(
                risk_level=RiskLevel.HIGH,
                reasons=["Uses biometric data"],
                requirements=["Human oversight required"],
            ),
        ):
            request = ExplainRequest(
                description="AI system uses facial recognition for recruitment screening of job applicants"
            )
            response = explain_risk(request)
            assert response.risk_level == RiskLevel.HIGH
            assert response.confidence > 0.7

    def test_minimal_risk_description_returns_minimal_risk(self):
        with patch(
            "app.api.v1.classification.classify_risk",
            return_value=MagicMock(
                risk_level=RiskLevel.MINIMAL,
                reasons=[],
                requirements=[],
            ),
        ):
            request = ExplainRequest(
                description="AI generates images of cats and dogs"
            )
            response = explain_risk(request)
            assert response.risk_level == RiskLevel.MINIMAL

    def test_returns_triggered_factors_for_recruitment(self):
        with patch(
            "app.api.v1.classification.classify_risk",
            return_value=MagicMock(
                risk_level=RiskLevel.HIGH,
                reasons=[],
                requirements=[],
            ),
        ):
            request = ExplainRequest(
                description="AI screens CVs and ranks candidates for hiring"
            )
            response = explain_risk(request)
            factor_ids = {f.factor_id for f in response.triggered_factors}
            assert "hr_recruitment_screening" in factor_ids

    def test_returns_relevant_articles(self):
        with patch(
            "app.api.v1.classification.classify_risk",
            return_value=MagicMock(
                risk_level=RiskLevel.HIGH,
                reasons=[],
                requirements=[],
            ),
        ):
            request = ExplainRequest(
                description="AI evaluates credit scores for loan decisions"
            )
            response = explain_risk(request)
            assert len(response.relevant_articles) > 0
            article_titles = {a.title for a in response.relevant_articles}
            assert "High-risk AI in Finance — Creditworthiness" in article_titles

    def test_returns_recommendations_for_high_risk(self):
        with patch(
            "app.api.v1.classification.classify_risk",
            return_value=MagicMock(
                risk_level=RiskLevel.HIGH,
                reasons=["Biometric data used"],
                requirements=["Conformity assessment required"],
            ),
        ):
            request = ExplainRequest(
                description="Facial recognition identifies users for authentication"
            )
            response = explain_risk(request)
            assert len(response.recommendations) > 0
            assert any("conformity assessment" in r.lower() for r in response.recommendations)
