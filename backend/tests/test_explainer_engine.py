"""
Unit tests for app.modules.explainer.engine — EU AI Act risk classification.

Covers:
- _normalize: lowercase and strip whitespace
- _extract_keywords: stop-word removal and keyword extraction
- _match_factors: keyword-to-risk-factor mapping
- _build_questionnaire: RiskClassificationRequest construction
- _compute_confidence: confidence score computation
- Edge cases: empty description, mixed-case keywords

Does not test explain_risk() end-to-end (requires DB + classify_risk).

Copyright (C) 2024 SdSarthak (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import pytest

from app.modules.explainer.engine import (
    _normalize,
    _extract_keywords,
    _match_factors,
    _build_questionnaire,
    _compute_confidence,
    FACTOR_KEYWORDS,
)
from app.models.ai_system import RiskLevel


class TestNormalize:
    """Tests for _normalize()."""

    def test_lowercases_text(self) -> None:
        assert _normalize("RECRUITMENT") == "recruitment"
        assert _normalize("Emotion Recognition") == "emotion recognition"

    def test_strips_whitespace(self) -> None:
        assert _normalize("  credit  ") == "credit"
        assert _normalize("\tloan\n") == "loan"

    def test_preserves_inner_spaces(self) -> None:
        assert _normalize("job application") == "job application"


class TestExtractKeywords:
    """Tests for _extract_keywords()."""

    def test_removes_stop_words(self) -> None:
        """Common stop words must be removed."""
        result = _extract_keywords("the system is used for hiring candidates")
        assert "the" not in result
        assert "is" not in result
        assert "for" not in result
        assert "the" not in result
        assert "system" not in result  # also a stop word in this impl
        assert "ai" not in result  # stop word

    def test_includes_meaningful_words(self) -> None:
        result = _extract_keywords("hiring candidates for recruitment screening")
        assert "recruitment" in result
        assert "candidates" in result

    def test_filters_short_words(self) -> None:
        """Words shorter than 3 chars are excluded."""
        result = _extract_keywords("a big cv for an ai")
        assert "cv" not in result  # 2 chars
        assert "ai" not in result  # 2 chars

    def test_empty_string_returns_empty_list(self) -> None:
        assert _extract_keywords("") == []
        assert _extract_keywords("   ") == []

    def test_mixed_case(self) -> None:
        """Keyword extraction is case-insensitive."""
        result = _extract_keywords("CREDIT scoring for LOAN decisions")
        assert "credit" in result
        assert "loan" in result


class TestMatchFactors:
    """Tests for _match_factors()."""

    def test_matches_recruitment_keywords(self) -> None:
        """'hiring' and 'candidate' should trigger hr_recruitment_screening."""
        result = _match_factors(
            "The system is used for hiring new candidates and screening CVs"
        )
        factor_ids = [fid for fid, _ in result]
        assert "hr_recruitment_screening" in factor_ids

    def test_matches_credit_keywords(self) -> None:
        """'credit' and 'loan' should trigger credit_worthiness."""
        result = _match_factors(
            "Evaluates creditworthiness for loan decisions"
        )
        factor_ids = [fid for fid, _ in result]
        assert "credit_worthiness" in factor_ids

    def test_matches_multiple_factors(self) -> None:
        """A description can trigger multiple risk factors."""
        result = _match_factors(
            "Used for hiring candidates and evaluating their credit for loans"
        )
        factor_ids = [fid for fid, _ in result]
        assert "hr_recruitment_screening" in factor_ids
        assert "credit_worthiness" in factor_ids

    def test_matches_biometric_keywords(self) -> None:
        result = _match_factors(
            "Facial recognition system for biometric verification"
        )
        factor_ids = [fid for fid, _ in result]
        assert "uses_biometric_data" in factor_ids

    def test_matches_automated_decision_keywords(self) -> None:
        result = _match_factors(
            "Automated decision making without human review"
        )
        factor_ids = [fid for fid, _ in result]
        assert "makes_automated_decisions" in factor_ids

    def test_matches_mixed_case_keywords(self) -> None:
        """Keyword matching must be case-insensitive."""
        result = _match_factors("CREDIT SCORE for LOAN")
        factor_ids = [fid for fid, _ in result]
        assert "credit_worthiness" in factor_ids

    def test_empty_description_returns_empty_list(self) -> None:
        result = _match_factors("")
        assert result == []

    def test_returns_matched_keywords(self) -> None:
        """Each tuple includes the matched keyword strings."""
        result = _match_factors("recruitment and hiring")
        matched = dict(result)
        assert "recruit" in matched["hr_recruitment_screening"]
        assert "hiring" in matched["hr_recruitment_screening"]

    def test_covers_all_factor_keyword_groups(self) -> None:
        """Verify that all defined FACTOR_KEYWORDS groups can be triggered."""
        all_triggered: list[str] = []
        for factor_id, keywords in FACTOR_KEYWORDS.items():
            for kw in keywords[:1]:  # just the first keyword per group
                result = _match_factors(kw)
                if result:
                    all_triggered.append(factor_id)
        # Every factor group should have at least one triggerable keyword
        assert len(all_triggered) == len(FACTOR_KEYWORDS), (
            f"Missing triggers for: {set(FACTOR_KEYWORDS) - set(all_triggered)}"
        )


class TestBuildQuestionnaire:
    """Tests for _build_questionnaire()."""

    def test_marks_matched_factors_true(self) -> None:
        q = _build_questionnaire(["hr_recruitment_screening", "credit_worthiness"])
        assert q.hr_recruitment_screening is True
        assert q.credit_worthiness is True

    def test_marks_unmatched_factors_false(self) -> None:
        q = _build_questionnaire(["hr_recruitment_screening"])
        assert q.credit_worthiness is False
        assert q.is_safety_component is False

    def test_empty_list_marks_all_false(self) -> None:
        q = _build_questionnaire([])
        assert q.hr_recruitment_screening is False
        assert q.credit_worthiness is False
        assert q.use_case_category == "other"

    def test_all_known_factors_accepted(self) -> None:
        """The function must not reject any known factor_id."""
        all_ids = list(FACTOR_KEYWORDS.keys())
        q = _build_questionnaire(all_ids)
        for fid in all_ids:
            assert getattr(q, fid) is True, f"{fid} should be True"


class TestComputeConfidence:
    """Tests for _compute_confidence()."""

    def test_no_matches_returns_075(self) -> None:
        """Zero matched factors = 0.75 confidence (minimal risk)."""
        result = _compute_confidence([], RiskLevel.MINIMAL)
        assert result == 0.75

    def test_single_keyword_low_confidence(self) -> None:
        """1 factor with 1 keyword = low-ish confidence (~0.70)."""
        matched = [("hr_recruitment_screening", ["recruit"])]
        result = _compute_confidence(matched, RiskLevel.HIGH)
        assert 0.65 <= result <= 0.80

    def test_multiple_keywords_increases_confidence(self) -> None:
        """More keyword matches increase confidence."""
        low = _compute_confidence(
            [("hr_recruitment_screening", ["recruit"])], RiskLevel.HIGH
        )
        high = _compute_confidence(
            [
                ("hr_recruitment_screening", ["recruit", "hiring", "candidate"]),
            ],
            RiskLevel.HIGH,
        )
        assert high > low

    def test_5plus_keywords_max_confidence(self) -> None:
        """5+ keyword matches approach max confidence (0.92+)."""
        matched = [
            (
                "hr_recruitment_screening",
                ["recruit", "hiring", "candidate", "cv", "screening"],
            ),
            ("credit_worthiness", ["loan"]),
        ]
        result = _compute_confidence(matched, RiskLevel.HIGH)
        assert result >= 0.92

    def test_multiple_factors_boosts_confidence(self) -> None:
        """3+ distinct factors give a small boost."""
        three_factors = [
            ("hr_recruitment_screening", ["recruit"]),
            ("credit_worthiness", ["loan"]),
            ("is_safety_component", ["vehicle"]),
        ]
        result = _compute_confidence(three_factors, RiskLevel.HIGH)
        # Should include the +0.05 boost
        assert result >= 0.75  # at minimum (base 0.70 + boost 0.05)

    def test_result_is_rounded_to_2dp(self) -> None:
        """Confidence must be rounded to 2 decimal places."""
        matched = [("hr_recruitment_screening", ["recruit"])]
        result = _compute_confidence(matched, RiskLevel.HIGH)
        assert result == round(result, 2)
