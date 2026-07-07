"""
Tests for backend/app/modules/compliance/eu_ai_act.py helpers.

Covers evaluate_compliance() and the _COMPLIANCE_STATUS_MAP.
"""

from __future__ import annotations

import pytest
from app.modules.compliance.eu_ai_act import (
    evaluate_compliance,
    _COMPLIANCE_STATUS_MAP,
    ComplianceStatus,
)


class TestEvaluateComplianceHighRisk:
    """Tests for high-risk AI system compliance evaluation."""

    def test_high_risk_returns_all_articles(self):
        """High-risk evaluation should return 11 requirement items."""
        items = evaluate_compliance("high", {})
        assert len(items) == 11
        assert all(isinstance(item.article_reference, str) for item in items)

    def test_article_references_are_correct(self):
        """Article references should match the EU AI Act articles."""
        items = evaluate_compliance("high", {})
        articles = [item.article_reference for item in items]
        assert "Article 9" in articles
        assert "Article 15" in articles
        assert "Article 43" in articles

    def test_missing_responses_gives_missing_status(self):
        """Requirements not in questionnaire should have 'missing' status."""
        items = evaluate_compliance("high", {})
        missing = [item for item in items if item.status == "missing"]
        assert len(missing) == 11  # all are missing when no responses

    def test_compliant_response_gives_done_status(self):
        """Compliant article responses should have 'done' status."""
        responses = {"article_9": "compliant"}
        items = evaluate_compliance("high", responses)
        done = [item for item in items if item.status == "done"]
        assert len(done) == 1
        assert done[0].article_reference == "Article 9"

    def test_in_progress_response_gives_partial_status(self):
        """In-progress responses should have 'partial' status."""
        responses = {"article_10": "in_progress"}
        items = evaluate_compliance("high", responses)
        partial = [item for item in items if item.status == "partial"]
        assert len(partial) == 1
        assert partial[0].article_reference == "Article 10"

    def test_under_review_maps_to_partial(self):
        """Under-review responses should map to 'partial'."""
        responses = {"article_9": "under_review"}
        items = evaluate_compliance("high", responses)
        item = next(item for item in items if item.article_reference == "Article 9")
        assert item.status == "partial"

    def test_non_compliant_maps_to_missing(self):
        """Non-compliant responses should map to 'missing'."""
        responses = {"article_9": "non_compliant"}
        items = evaluate_compliance("high", responses)
        item = next(item for item in items if item.article_reference == "Article 9")
        assert item.status == "missing"

    def test_action_needed_populated_for_incomplete(self):
        """Action_needed should be non-empty for items not marked done."""
        responses = {"article_9": "not_started"}
        items = evaluate_compliance("high", responses)
        item = next(item for item in items if item.article_reference == "Article 9")
        assert item.action_needed != ""
        assert "risk management" in item.action_needed.lower()

    def test_action_needed_empty_for_done(self):
        """Action_needed should be empty for items marked done."""
        responses = {"article_9": "compliant"}
        items = evaluate_compliance("high", responses)
        item = next(item for item in items if item.article_reference == "Article 9")
        assert item.action_needed == ""

    def test_whitespace_in_key_is_handled(self):
        """Whitespace in questionnaire keys should not cause false negatives."""
        responses = {" article_9 ": "compliant"}
        items = evaluate_compliance("high", responses)
        item = next(item for item in items if item.article_reference == "Article 9")
        assert item.status == "done"

    def test_invalid_status_defaults_to_missing(self):
        """Invalid status values should default to 'missing'."""
        responses = {"article_9": "garbage_value"}
        items = evaluate_compliance("high", responses)
        item = next(item for item in items if item.article_reference == "Article 9")
        assert item.status == "missing"

    def test_case_insensitive_risk_level(self):
        """Risk level should be case-insensitive."""
        items_lower = evaluate_compliance("high", {})
        items_upper = evaluate_compliance("HIGH", {})
        assert len(items_lower) == len(items_upper)
        assert items_lower[0].article_reference == items_upper[0].article_reference


class TestEvaluateComplianceLimitedRisk:
    """Tests for limited-risk AI system compliance evaluation."""

    def test_limited_risk_returns_2_articles(self):
        """Limited-risk evaluation should return 2 requirement items."""
        items = evaluate_compliance("limited", {})
        assert len(items) == 2

    def test_limited_risk_disclosure_requirements(self):
        """Limited-risk systems need transparency disclosures."""
        items = evaluate_compliance("limited", {})
        articles = [item.article_reference for item in items]
        assert "Article 50(1)" in articles
        assert "Article 50(2)" in articles


class TestEvaluateComplianceMinimalRisk:
    """Tests for minimal-risk AI system compliance evaluation."""

    def test_minimal_risk_returns_voluntary_code(self):
        """Minimal-risk should return the voluntary code of conduct item."""
        items = evaluate_compliance("minimal", {})
        assert len(items) == 1
        assert "voluntarily" in items[0].requirement.lower() or "voluntary" in items[0].requirement.lower()


class TestEvaluateComplianceUnacceptableRisk:
    """Tests for unacceptable-risk AI system compliance evaluation."""

    def test_unacceptable_risk_returns_prohibited_notice(self):
        """Unacceptable-risk systems should return a prohibition notice."""
        items = evaluate_compliance("unacceptable", {})
        assert len(items) == 1
        assert "prohibited" in items[0].requirement.lower() or "prohibited" in items[0].article_reference.lower()


class TestEvaluateComplianceEdgeCases:
    """Edge-case tests for evaluate_compliance()."""

    def test_unknown_risk_level_returns_empty_list(self):
        """Unknown risk level should return an empty list."""
        items = evaluate_compliance("unknown_level", {})
        assert items == []

    def test_empty_questionnaire_responses_handled(self):
        """Empty dict responses should be handled gracefully."""
        items = evaluate_compliance("high", {})
        assert len(items) == 11
        assert all(item.status == "missing" for item in items)

    def test_requirement_description_always_populated(self):
        """Requirement description should always be a non-empty string."""
        items = evaluate_compliance("high", {})
        for item in items:
            assert item.requirement
            assert isinstance(item.requirement, str)
            assert len(item.requirement) > 0
