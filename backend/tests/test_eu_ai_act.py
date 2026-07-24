"""
Tests for EU AI Act compliance evaluation logic.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import pytest

from app.modules.compliance.eu_ai_act import (
    evaluate_compliance,
    _COMPLIANCE_STATUS_MAP,
    RequirementItem,
    ComplianceStatus,
)


class TestEvaluateCompliance:
    def test_high_risk_returns_all_articles(self):
        """High-risk systems must return all EU AI Act requirement items."""
        result = evaluate_compliance("high", {})
        assert len(result) == 11
        assert all(isinstance(item, RequirementItem) for item in result)
        assert all(item.status == "missing" for item in result)

    def test_high_risk_article_references(self):
        """High-risk items should include all specified article references."""
        result = evaluate_compliance("high", {})
        articles = {item.article_reference for item in result}
        expected = {
            "Article 9", "Article 10", "Article 11", "Article 12",
            "Article 13", "Article 14", "Article 15", "Article 43",
            "Article 49", "Article 72", "Article 73",
        }
        assert articles == expected

    def test_limited_risk_returns_two_articles(self):
        """Limited-risk systems map to transparency obligations."""
        result = evaluate_compliance("limited", {})
        assert len(result) == 2
        articles = {item.article_reference for item in result}
        assert articles == {"Article 50(1)", "Article 50(2)"}

    def test_minimal_risk_returns_one_item(self):
        """Minimal-risk systems have a single voluntary code item."""
        result = evaluate_compliance("minimal", {})
        assert len(result) == 1
        assert "Recital 48" in result[0].article_reference

    def test_unacceptable_risk_returns_prohibited_item(self):
        """Unacceptable-risk systems are prohibited under Article 5."""
        result = evaluate_compliance("unacceptable", {})
        assert len(result) == 1
        assert "PROHIBITED" in result[0].requirement
        assert "Article 5" in result[0].article_reference

    def test_unknown_risk_level_returns_empty(self):
        """Unknown risk levels should not crash and return an empty list."""
        result = evaluate_compliance("unknown_level", {})
        assert result == []

    def test_unknown_risk_level_case_insensitive(self):
        """Risk level matching is case-insensitive."""
        result = evaluate_compliance("HIGH", {})
        assert len(result) == 11
        result2 = evaluate_compliance("  High  ", {})
        assert len(result2) == 11

    def test_questionnaire_done_status(self):
        """Completed requirements should have status 'done' and no action."""
        responses = {"article_9": "done", "article_10": "done"}
        result = evaluate_compliance("high", responses)
        article9 = next(i for i in result if i.article_reference == "Article 9")
        assert article9.status == "done"
        assert article9.action_needed == ""

    def test_questionnaire_partial_status(self):
        """In-progress requirements should have status 'partial' and an action."""
        responses = {"article_9": "partial"}
        result = evaluate_compliance("high", responses)
        article9 = next(i for i in result if i.article_reference == "Article 9")
        assert article9.status == "partial"
        assert article9.action_needed != ""

    def test_questionnaire_missing_status(self):
        """Not-started requirements should have status 'missing'."""
        responses = {}
        result = evaluate_compliance("high", responses)
        for item in result:
            assert item.status == "missing"

    def test_invalid_questionnaire_value_defaults_to_missing(self):
        """Invalid status values in questionnaire default to 'missing'."""
        responses = {"article_9": "invalid_status"}
        result = evaluate_compliance("high", responses)
        article9 = next(i for i in result if i.article_reference == "Article 9")
        assert article9.status == "missing"

    def test_compliance_status_map_compliant(self):
        """'compliant' maps to 'done' status."""
        responses = {"article_9": "compliant"}
        result = evaluate_compliance("high", responses)
        article9 = next(i for i in result if i.article_reference == "Article 9")
        assert article9.status == "done"

    def test_compliance_status_map_in_progress(self):
        """'in_progress' maps to 'partial' status."""
        responses = {"article_9": "in_progress"}
        result = evaluate_compliance("high", responses)
        article9 = next(i for i in result if i.article_reference == "Article 9")
        assert article9.status == "partial"

    def test_compliance_status_map_under_review(self):
        """'under_review' maps to 'partial' status."""
        responses = {"article_9": "under_review"}
        result = evaluate_compliance("high", responses)
        article9 = next(i for i in result if i.article_reference == "Article 9")
        assert article9.status == "partial"

    def test_compliance_status_map_not_started(self):
        """'not_started' maps to 'missing' status."""
        responses = {"article_9": "not_started"}
        result = evaluate_compliance("high", responses)
        article9 = next(i for i in result if i.article_reference == "Article 9")
        assert article9.status == "missing"

    def test_compliance_status_map_non_compliant(self):
        """'non_compliant' maps to 'missing' status."""
        responses = {"article_9": "non_compliant"}
        result = evaluate_compliance("high", responses)
        article9 = next(i for i in result if i.article_reference == "Article 9")
        assert article9.status == "missing"

    def test_requirement_item_is_frozen_dataclass(self):
        """RequirementItem must be immutable."""
        result = evaluate_compliance("high", {})
        item = result[0]
        with pytest.raises(AttributeError):
            item.status = "done"

    def test_action_needed_populated_for_incomplete(self):
        """Every incomplete requirement must have a non-empty action."""
        responses = {}
        result = evaluate_compliance("high", responses)
        for item in result:
            assert item.action_needed != ""

    def test_requirement_field_populated(self):
        """Each requirement item must have a non-empty requirement string."""
        result = evaluate_compliance("high", {})
        for item in result:
            assert item.requirement
            assert len(item.requirement) > 10
