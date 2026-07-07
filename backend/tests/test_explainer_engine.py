"""
Unit tests for backend/app/modules/explainer/engine.py —
risk classification explainer helpers.
"""

import pytest

from app.modules.explainer.engine import (
    _extract_keywords,
    _match_factors,
    _normalize,
)


class TestNormalize:
    """Tests for _normalize — lowercase and strip."""

    def test_lowercase(self):
        assert _normalize("HELLO WORLD") == "hello world"

    def test_strips_whitespace(self):
        assert _normalize("  hello  ") == "hello"
        assert _normalize("hello\n") == "hello"

    def test_preserves_middle_whitespace(self):
        assert _normalize("hello world") == "hello world"


class TestExtractKeywords:
    """Tests for _extract_keywords — removes stop words, keeps 3+ char words."""

    def test_removes_stop_words(self):
        keywords = _extract_keywords("the system is an AI model for hiring")
        assert "the" not in keywords
        assert "system" not in keywords
        assert "ai" not in keywords  # in stop_words
        assert "model" not in keywords  # in stop_words

    def test_keeps_meaningful_words(self):
        keywords = _extract_keywords("recruitment screening for job applications")
        assert "recruitment" in keywords
        assert "screening" in keywords
        assert "job" in keywords
        assert "applications" in keywords

    def test_filters_short_words(self):
        keywords = _extract_keywords("a i bc def")
        assert "def" in keywords
        assert "bc" not in keywords
        assert "i" not in keywords

    def test_empty_description(self):
        assert _extract_keywords("") == []
        assert _extract_keywords("  the a an  ") == []

    def test_no_duplicates(self):
        keywords = _extract_keywords("recruit recruitment recruiting")
        # All three contain "recruit"
        assert len([k for k in keywords if k == "recruit"]) == 1


class TestMatchFactors:
    """Tests for _match_factors — maps description text to EU AI Act risk factors."""

    def test_matches_hr_recruitment_keywords(self):
        matched = _match_factors("AI tool for recruitment and hiring candidates")
        factor_ids = [f[0] for f in matched]
        assert "hr_recruitment_screening" in factor_ids

    def test_matches_credit_worthiness_keywords(self):
        matched = _match_factors("credit score lending decision for mortgage")
        factor_ids = [f[0] for f in matched]
        assert "credit_worthiness" in factor_ids

    def test_matches_multiple_factors(self):
        matched = _match_factors(
            "AI for recruitment screening and credit worthiness assessment"
        )
        factor_ids = [f[0] for f in matched]
        assert "hr_recruitment_screening" in factor_ids
        assert "credit_worthiness" in factor_ids

    def test_no_matches_returns_empty(self):
        matched = _match_factors("AI chess game")
        assert matched == []

    def test_returns_matched_keywords(self):
        matched = _match_factors("recruitment and hiring")
        for factor_id, keywords in matched:
            if factor_id == "hr_recruitment_screening":
                assert len(keywords) >= 2  # "recruitment" and "hiring" both matched
