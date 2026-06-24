"""
Unit tests for backend/app/modules/explainer/engine.py.

The explainer engine is a pure-Python offline module with no external
dependencies (no LLM, no API calls). Tests are fast and fully deterministic.
"""

import pytest

from app.modules.explainer.engine import (
    _normalize,
    _extract_keywords,
    _match_factors,
    _compute_confidence,
    _build_questionnaire,
    FACTOR_KEYWORDS,
    ARTICLE_LIBRARY,
    RECOMMENDATIONS,
)
from app.schemas.explain import ExplainRequest, ExplainResponse
from app.models.ai_system import RiskLevel


class TestNormalize:
    def test_lowercases(self):
        assert _normalize("HELLO WORLD") == "hello world"

    def test_strips_whitespace(self):
        assert _normalize("  hello  ") == "hello"

    def test_preserves_internal_spaces(self):
        assert _normalize("hello world") == "hello world"


class TestExtractKeywords:
    def test_removes_stop_words(self):
        keywords = _extract_keywords(
            "The AI system is used for hiring and evaluating employees"
        )
        assert "the" not in keywords
        assert "is" not in keywords
        assert "for" not in keywords
        assert "and" not in keywords

    def test_includes_recruitment_keywords(self):
        keywords = _extract_keywords(
            "Our AI screens CVs and ranks job applicants during recruitment"
        )
        assert "recruit" in keywords
        assert "cv" in keywords
        assert "screening" in keywords
        assert "job" in keywords

    def test_minimum_word_length(self):
        keywords = _extract_keywords("a ai is")
        assert "a" not in keywords
        assert "ai" not in keywords  # 2 chars < 3

    def test_empty_description(self):
        keywords = _extract_keywords("")
        assert keywords == []

    def test_no_duplicates(self):
        keywords = _extract_keywords(
            "recruit recruit recruitment hiring hiring hire"
        )
        # After stop-word removal, only "recruit", "recruitment", "hiring", "hire" remain
        assert len(keywords) == len(set(keywords))


class TestMatchFactors:
    def test_hr_recruitment_screening_triggered(self):
        matched = _match_factors(
            "An AI that screens CVs and ranks candidates during hiring"
        )
        factor_ids = [fid for fid, _ in matched]
        assert "hr_recruitment_screening" in factor_ids

    def test_credit_worthiness_triggered(self):
        matched = _match_factors(
            "AI system that evaluates creditworthiness for loan decisions"
        )
        factor_ids = [fid for fid, _ in matched]
        assert "credit_worthiness" in factor_ids

    def test_safety_component_triggered(self):
        matched = _match_factors(
            "AI used as a safety component in autonomous vehicles"
        )
        factor_ids = [fid for fid, _ in matched]
        assert "is_safety_component" in factor_ids

    def test_biometric_triggered(self):
        matched = _match_factors(
            "Facial recognition system for biometric identification"
        )
        factor_ids = [fid for fid, _ in matched]
        assert "uses_biometric_data" in factor_ids

    def test_law_enforcement_triggered(self):
        matched = _match_factors(
            "AI for crime prediction and police surveillance"
        )
        factor_ids = [fid for fid, _ in matched]
        assert "law_enforcement" in factor_ids

    def test_no_match_returns_empty(self):
        matched = _match_factors(
            "A simple calculator that adds two numbers together"
        )
        assert matched == []

    def test_multiple_factors_triggered(self):
        matched = _match_factors(
            "AI for hiring that also evaluates employee performance and credit"
        )
        factor_ids = [fid for fid, _ in matched]
        assert "hr_recruitment_screening" in factor_ids
        assert "hr_promotion_termination" in factor_ids
        assert "credit_worthiness" in factor_ids

    def test_returns_matched_keywords(self):
        matched = _match_factors(
            "An AI that screens CVs during recruitment"
        )
        for factor_id, keywords in matched:
            if factor_id == "hr_recruitment_screening":
                assert "recruit" in keywords or "cv" in keywords


class TestComputeConfidence:
    def test_no_matches_returns_075(self):
        confidence = _compute_confidence([], RiskLevel.MINIMAL)
        assert confidence == 0.75

    def test_single_keyword_low_confidence(self):
        # One factor with one keyword match
        matched = [("hr_recruitment_screening", ["recruit"])]
        confidence = _compute_confidence(matched, RiskLevel.LIMITED)
        assert 0.6 <= confidence <= 0.8

    def test_many_keywords_high_confidence(self):
        # Two factors with many keywords each
        matched = [
            ("hr_recruitment_screening", ["recruit", "recruitment", "cv", "hiring", "job"]),
            ("hr_promotion_termination", ["promot", "terminat", "layoff", "performance"]),
        ]
        confidence = _compute_confidence(matched, RiskLevel.HIGH)
        assert confidence >= 0.85

    def test_confidence_bounded_by_097(self):
        matched = [
            ("hr_recruitment_screening", ["recruit", "recruitment", "cv", "hiring", "job"]),
            ("hr_promotion_termination", ["promot", "terminat", "layoff", "performance"]),
            ("credit_worthiness", ["credit", "loan", "mortgage", "debt"]),
        ]
        confidence = _compute_confidence(matched, RiskLevel.HIGH)
        assert confidence <= 0.97


class TestBuildQuestionnaire:
    def test_matched_factor_set_true(self):
        questionnaire = _build_questionnaire(["hr_recruitment_screening"])
        assert questionnaire.hr_recruitment_screening is True

    def test_unmatched_factors_default_false(self):
        questionnaire = _build_questionnaire(["hr_recruitment_screening"])
        assert questionnaire.hr_promotion_termination is False
        assert questionnaire.credit_worthiness is False
        assert questionnaire.uses_biometric_data is False

    def test_multiple_matched_factors(self):
        questionnaire = _build_questionnaire([
            "hr_recruitment_screening",
            "credit_worthiness",
        ])
        assert questionnaire.hr_recruitment_screening is True
        assert questionnaire.credit_worthiness is True

    def test_use_case_category_defaults_to_other(self):
        questionnaire = _build_questionnaire([])
        assert questionnaire.use_case_category == "other"


class TestRecommendations:
    def test_high_risk_has_multiple_recommendations(self):
        recs = RECOMMENDATIONS[RiskLevel.HIGH]
        assert len(recs) >= 5
        assert any("conformity" in r.lower() for r in recs)

    def test_limited_risk_has_disclosure_notices(self):
        recs = RECOMMENDATIONS[RiskLevel.LIMITED]
        assert len(recs) >= 3
        assert any("disclosure" in r.lower() for r in recs)

    def test_minimal_risk_has_voluntary_codes(self):
        recs = RECOMMENDATIONS[RiskLevel.MINIMAL]
        assert len(recs) >= 3
        assert any("voluntary" in r.lower() for r in recs)


class TestArticleLibrary:
    def test_all_factor_ids_have_articles(self):
        for factor_id in FACTOR_KEYWORDS:
            assert factor_id in ARTICLE_LIBRARY, f"Missing article for {factor_id}"

    def test_article_has_required_fields(self):
        for factor_id, article in ARTICLE_LIBRARY.items():
            assert article.article, f"{factor_id}: missing article reference"
            assert article.title, f"{factor_id}: missing title"
            assert article.summary, f"{factor_id}: missing summary"
