"""Unit tests for backend/app/modules/compliance/eu_ai_act.py EU AI Act compliance evaluation."""

import pytest

from app.modules.compliance.eu_ai_act import (
    RequirementItem,
    evaluate_compliance,
)


class TestEvaluateCompliance:
    """Tests for evaluate_compliance function."""

    def test_high_risk_returns_all_high_risk_rules(self):
        """evaluate_compliance returns all high-risk EU AI Act rules for risk_level=high."""
        result = evaluate_compliance("high", {})
        assert len(result) == 12  # 12 high-risk rules defined

    def test_high_risk_all_items_are_requirement_item(self):
        """All returned items are RequirementItem instances."""
        result = evaluate_compliance("high", {})
        assert all(isinstance(item, RequirementItem) for item in result)

    def test_high_risk_articles_include_all_article_references(self):
        """High-risk items cover the expected article references."""
        result = evaluate_compliance("high", {})
        articles = {item.article_reference for item in result}
        expected = {
            "Article 9",
            "Article 10",
            "Article 11",
            "Article 12",
            "Article 13",
            "Article 14",
            "Article 15",
            "Article 43",
            "Article 49",
            "Article 72",
            "Article 73",
        }
        assert articles == expected

    def test_limited_risk_returns_limited_rules(self):
        """evaluate_compliance returns limited-risk rules for risk_level=limited."""
        result = evaluate_compliance("limited", {})
        assert len(result) == 2  # 2 limited-risk rules defined
        articles = {item.article_reference for item in result}
        assert "Article 50(1)" in articles
        assert "Article 50(2)" in articles

    def test_minimal_risk_returns_minimal_rules(self):
        """evaluate_compliance returns minimal-risk rules for risk_level=minimal."""
        result = evaluate_compliance("minimal", {})
        assert len(result) == 1
        assert "Recital 48" in result[0].article_reference

    def test_unacceptable_risk_returns_prohibition_notice(self):
        """evaluate_compliance returns unacceptable-risk rules for risk_level=unacceptable."""
        result = evaluate_compliance("unacceptable", {})
        assert len(result) == 1
        assert "PROHIBITED" in result[0].requirement
        assert result[0].status == "missing"

    def test_unknown_risk_level_returns_empty_list(self):
        """evaluate_compliance returns empty list for unknown risk level."""
        result = evaluate_compliance("unknown_risk_level", {})
        assert result == []

    def test_case_insensitive_risk_level(self):
        """evaluate_compliance handles risk levels case-insensitively."""
        result_upper = evaluate_compliance("HIGH", {})
        result_lower = evaluate_compliance("high", {})
        assert len(result_upper) == len(result_lower)

    def test_risk_level_with_whitespace(self):
        """evaluate_compliance strips whitespace from risk level."""
        result = evaluate_compliance("  high  ", {})
        assert len(result) == 12

    def test_status_mapping_compliant_maps_to_done(self):
        """Status 'compliant' maps to requirement status 'done'."""
        result = evaluate_compliance("high", {"article_9": "compliant"})
        article_9 = next(item for item in result if "Article 9" in item.article_reference)
        assert article_9.status == "done"

    def test_status_mapping_in_progress_maps_to_partial(self):
        """Status 'in_progress' maps to requirement status 'partial'."""
        result = evaluate_compliance("high", {"article_9": "in_progress"})
        article_9 = next(item for item in result if "Article 9" in item.article_reference)
        assert article_9.status == "partial"

    def test_status_mapping_under_review_maps_to_partial(self):
        """Status 'under_review' maps to requirement status 'partial'."""
        result = evaluate_compliance("high", {"article_9": "under_review"})
        article_9 = next(item for item in result if "Article 9" in item.article_reference)
        assert article_9.status == "partial"

    def test_status_mapping_not_started_maps_to_missing(self):
        """Status 'not_started' maps to requirement status 'missing'."""
        result = evaluate_compliance("high", {"article_9": "not_started"})
        article_9 = next(item for item in result if "Article 9" in item.article_reference)
        assert article_9.status == "missing"

    def test_status_mapping_non_compliant_maps_to_missing(self):
        """Status 'non_compliant' maps to requirement status 'missing'."""
        result = evaluate_compliance("high", {"article_9": "non_compliant"})
        article_9 = next(item for item in result if "Article 9" in item.article_reference)
        assert article_9.status == "missing"

    def test_action_needed_populated_for_non_done_status(self):
        """action_needed field is non-empty when status is not 'done'."""
        result = evaluate_compliance("high", {"article_9": "not_started"})
        article_9 = next(item for item in result if "Article 9" in item.article_reference)
        assert article_9.action_needed != ""

    def test_action_needed_empty_for_done_status(self):
        """action_needed field is empty when status is 'done'."""
        result = evaluate_compliance("high", {"article_9": "compliant"})
        article_9 = next(item for item in result if "Article 9" in item.article_reference)
        assert article_9.action_needed == ""

    def test_unknown_status_defaults_to_missing(self):
        """Unknown status value defaults to 'missing'."""
        result = evaluate_compliance("high", {"article_9": "some_random_status"})
        article_9 = next(item for item in result if "Article 9" in item.article_reference)
        assert article_9.status == "missing"

    def test_strips_whitespace_from_questionnaire_values(self):
        """Questionnaire values with leading/trailing whitespace are stripped."""
        result = evaluate_compliance("high", {"article_9": "  compliant  "})
        article_9 = next(item for item in result if "Article 9" in item.article_reference)
        assert article_9.status == "done"

    def test_strips_whitespace_from_questionnaire_keys(self):
        """Questionnaire keys with leading/trailing whitespace are matched."""
        result = evaluate_compliance("high", {"  article_9  ": "compliant"})
        article_9 = next(item for item in result if "Article 9" in item.article_reference)
        assert article_9.status == "done"
