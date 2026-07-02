"""
Unit tests for backend/app/modules/compliance/eu_ai_act.py.

Covers evaluate_compliance() key transformation, status fallback matching,
risk level mapping, and RequirementItem field validation.
"""

import pytest
from app.modules.compliance.eu_ai_act import (
    evaluate_compliance,
    RequirementItem,
    ComplianceStatus,
)


class TestEvaluateComplianceHighRisk:
    """Test high-risk compliance evaluation."""

    def test_empty_questionnaire_all_missing(self):
        """Empty questionnaire responses -> all requirements status 'missing'."""
        results = evaluate_compliance("high", {})
        assert len(results) == 11  # _HIGH_RISK_RULES has 11 entries
        for item in results:
            assert item.status == "missing"
            assert item.action_needed != ""  # missing -> has action_needed

    def test_article_9_compliant_maps_to_done(self):
        """{'article_9': 'compliant'} -> article 9 status 'done', action_needed=''."""
        results = evaluate_compliance("high", {"article_9": "compliant"})
        article_9_item = next(i for i in results if i.article_reference == "Article 9")
        assert article_9_item.status == "done"
        assert article_9_item.action_needed == ""

    def test_article_9_in_progress_maps_to_partial(self):
        """{'article_9': 'in_progress'} -> status 'partial'."""
        results = evaluate_compliance("high", {"article_9": "in_progress"})
        article_9_item = next(i for i in results if i.article_reference == "Article 9")
        assert article_9_item.status == "partial"

    def test_article_9_under_review_maps_to_partial(self):
        """{'article_9': 'under_review'} -> status 'partial'."""
        results = evaluate_compliance("high", {"article_9": "under_review"})
        article_9_item = next(i for i in results if i.article_reference == "Article 9")
        assert article_9_item.status == "partial"

    def test_article_9_not_started_maps_to_missing(self):
        """{'article_9': 'not_started'} -> status 'missing'."""
        results = evaluate_compliance("high", {"article_9": "not_started"})
        article_9_item = next(i for i in results if i.article_reference == "Article 9")
        assert article_9_item.status == "missing"

    def test_article_9_non_compliant_maps_to_missing(self):
        """{'article_9': 'non_compliant'} -> status 'missing'."""
        results = evaluate_compliance("high", {"article_9": "non_compliant"})
        article_9_item = next(i for i in results if i.article_reference == "Article 9")
        assert article_9_item.status == "missing"

    def test_whitespace_stripped_in_key(self):
        """Keys with leading/trailing whitespace are matched correctly."""
        results = evaluate_compliance("high", {" article_9 ": "compliant"})
        article_9_item = next(i for i in results if i.article_reference == "Article 9")
        assert article_9_item.status == "done"

    def test_whitespace_stripped_in_value(self):
        """Values with leading/trailing whitespace are stripped."""
        results = evaluate_compliance("high", {"article_9": "  compliant  "})
        article_9_item = next(i for i in results if i.article_reference == "Article 9")
        assert article_9_item.status == "done"

    def test_invalid_status_value_defaults_to_missing(self):
        """Unknown status string -> 'missing'."""
        results = evaluate_compliance("high", {"article_9": "random_invalid_status"})
        article_9_item = next(i for i in results if i.article_reference == "Article 9")
        assert article_9_item.status == "missing"

    def test_risk_level_case_insensitive(self):
        """risk_level is case-insensitive."""
        results_upper = evaluate_compliance("HIGH", {})
        results_lower = evaluate_compliance("high", {})
        assert len(results_upper) == len(results_lower)
        assert len(results_upper) == 11
        for u, l in zip(results_upper, results_lower):
            assert u.article_reference == l.article_reference

    def test_risk_level_whitespace_trimmed(self):
        """risk_level with leading/trailing whitespace is trimmed."""
        results = evaluate_compliance("  high  ", {})
        assert len(results) == 11


class TestEvaluateComplianceRiskLevels:
    """Test all risk levels return the correct rules."""

    def test_high_risk_returns_11_items(self):
        """HIGH risk -> 11 requirement items."""
        results = evaluate_compliance("high", {})
        assert len(results) == 11
        refs = {i.article_reference for i in results}
        assert "Article 9" in refs
        assert "Article 15" in refs

    def test_limited_risk_returns_2_items(self):
        """LIMITED risk -> 2 requirement items."""
        results = evaluate_compliance("limited", {})
        assert len(results) == 2
        refs = {i.article_reference for i in results}
        assert "Article 50(1)" in refs
        assert "Article 50(2)" in refs

    def test_minimal_risk_returns_1_item(self):
        """MINIMAL risk -> 1 requirement item."""
        results = evaluate_compliance("minimal", {})
        assert len(results) == 1
        assert "Recital 48" in results[0].article_reference

    def test_unacceptable_risk_returns_1_item(self):
        """UNACCEPTABLE risk -> 1 requirement item."""
        results = evaluate_compliance("unacceptable", {})
        assert len(results) == 1
        assert results[0].article_reference == "Article 5"
        assert results[0].status == "missing"  # no response provided

    def test_unknown_risk_level_returns_empty_list(self):
        """Unknown risk level -> empty list."""
        results = evaluate_compliance("nonexistent_risk", {})
        assert results == []


class TestRequirementItemFields:
    """Test RequirementItem dataclass fields are populated correctly."""

    def test_done_item_action_needed_empty(self):
        """Status 'done' -> action_needed is empty string."""
        results = evaluate_compliance("high", {"article_9": "compliant"})
        item = next(i for i in results if i.article_reference == "Article 9")
        assert item.action_needed == ""
        assert item.status == "done"

    def test_missing_item_has_action_needed(self):
        """Status 'missing' -> action_needed contains guidance text."""
        results = evaluate_compliance("high", {})
        item = next(i for i in results if i.article_reference == "Article 9")
        assert item.action_needed != ""
        assert isinstance(item.action_needed, str)

    def test_partial_item_has_action_needed(self):
        """Status 'partial' -> action_needed contains guidance text."""
        results = evaluate_compliance("high", {"article_9": "in_progress"})
        item = next(i for i in results if i.article_reference == "Article 9")
        assert item.action_needed != ""
        assert item.status == "partial"

    def test_requirement_field_populated(self):
        """requirement field contains EU AI Act description text."""
        results = evaluate_compliance("high", {})
        for item in results:
            assert item.requirement != ""
            assert len(item.requirement) > 10

    def test_article_reference_matches_rules(self):
        """article_reference matches the source rule."""
        results = evaluate_compliance("high", {"article_12": "compliant"})
        item = next(i for i in results if i.article_reference == "Article 12")
        assert "logging" in item.requirement.lower() or "traceability" in item.requirement.lower()


class TestComplianceStatusType:
    """Test ComplianceStatus literal type."""

    def test_status_is_valid_literal(self):
        """All returned statuses are valid ComplianceStatus literals."""
        test_cases = [
            ({"article_9": "compliant"}, "done"),
            ({"article_9": "in_progress"}, "partial"),
            ({"article_9": "under_review"}, "partial"),
            ({"article_9": "not_started"}, "missing"),
            ({"article_9": "non_compliant"}, "missing"),
            ({}, "missing"),
        ]
        results = evaluate_compliance("high", {})
        for questionnaire, expected_status in test_cases:
            results = evaluate_compliance("high", questionnaire)
            item = next(i for i in results if i.article_reference == "Article 9")
            assert item.status == expected_status
