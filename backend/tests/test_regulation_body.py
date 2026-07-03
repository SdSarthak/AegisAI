"""
Unit tests for app/plugins/schema.py — RegulationBody model_validator.

Tests cover:
  - RegulationBody accepts valid regulation data
  - RegulationBody rejects maps_to referencing non-existent risk_factor ids
  - RegulationBody error message lists all invalid mappings
  - RiskFactor rejects extra fields (extra='forbid')
  - ComplianceQuestion rejects extra fields (extra='forbid')
"""

import pytest
from pydantic import ValidationError

from app.plugins.schema import (
    ComplianceQuestion,
    RegulationBody,
    RiskFactor,
)


class TestRiskFactor:
    def test_accepts_valid_risk_factor(self):
        rf = RiskFactor(id="rf-1", label="Discrimination", severity="high")
        assert rf.id == "rf-1"
        assert rf.label == "Discrimination"
        assert rf.severity == "high"

    def test_rejects_extra_fields(self):
        with pytest.raises(ValidationError) as exc_info:
            RiskFactor(id="rf-1", label="Discrimination", severity="high", extra_field="x")
        assert "extra_forbidden" in str(exc_info.value)


class TestComplianceQuestion:
    def test_accepts_valid_question(self):
        q = ComplianceQuestion(id="q-1", text="Is this fair?", maps_to="rf-1")
        assert q.id == "q-1"
        assert q.text == "Is this fair?"
        assert q.maps_to == "rf-1"

    def test_rejects_extra_fields(self):
        with pytest.raises(ValidationError) as exc_info:
            ComplianceQuestion(id="q-1", text="Is this fair?", maps_to="rf-1", extra="bad")
        assert "extra_forbidden" in str(exc_info.value)


class TestRegulationBody:
    def test_accepts_valid_regulation(self):
        body = RegulationBody(
            name="EU AI Act",
            version="1.0",
            risk_factors=[
                RiskFactor(id="rf-1", label="Discrimination", severity="high"),
                RiskFactor(id="rf-2", label="Safety Risk", severity="high"),
            ],
            prohibited_uses=["Social scoring"],
            required_documents=["Conformity assessment report"],
            compliance_questions=[
                ComplianceQuestion(id="q-1", text="Is this fair?", maps_to="rf-1"),
                ComplianceQuestion(id="q-2", text="Is this safe?", maps_to="rf-2"),
            ],
        )
        assert body.name == "EU AI Act"
        assert len(body.risk_factors) == 2
        assert len(body.compliance_questions) == 2

    def test_rejects_invalid_maps_to_reference(self):
        with pytest.raises(ValidationError) as exc_info:
            RegulationBody(
                name="EU AI Act",
                version="1.0",
                risk_factors=[
                    RiskFactor(id="rf-1", label="Discrimination", severity="high"),
                ],
                prohibited_uses=["Social scoring"],
                required_documents=["Report"],
                compliance_questions=[
                    ComplianceQuestion(id="q-1", text="Is this fair?", maps_to="rf-does-not-exist"),
                ],
            )
        assert "Invalid maps_to references" in str(exc_info.value)
        assert "rf-does-not-exist" in str(exc_info.value)

    def test_error_lists_all_invalid_mappings(self):
        with pytest.raises(ValidationError) as exc_info:
            RegulationBody(
                name="EU AI Act",
                version="1.0",
                risk_factors=[
                    RiskFactor(id="rf-1", label="Discrimination", severity="high"),
                ],
                prohibited_uses=["Social scoring"],
                required_documents=["Report"],
                compliance_questions=[
                    ComplianceQuestion(id="q-1", text="Q1", maps_to="rf-1"),
                    ComplianceQuestion(id="q-2", text="Q2", maps_to="rf-bad-1"),
                    ComplianceQuestion(id="q-3", text="Q3", maps_to="rf-bad-2"),
                ],
            )
        error_msg = str(exc_info.value)
        assert "rf-bad-1" in error_msg
        assert "rf-bad-2" in error_msg

    def test_rejects_empty_risk_factors(self):
        with pytest.raises(ValidationError) as exc_info:
            RegulationBody(
                name="EU AI Act",
                version="1.0",
                risk_factors=[],
                prohibited_uses=["Social scoring"],
                required_documents=["Report"],
                compliance_questions=[
                    ComplianceQuestion(id="q-1", text="Q1", maps_to="rf-1"),
                ],
            )
        assert "too_short" in str(exc_info.value)

    def test_rejects_empty_prohibited_uses(self):
        with pytest.raises(ValidationError) as exc_info:
            RegulationBody(
                name="EU AI Act",
                version="1.0",
                risk_factors=[
                    RiskFactor(id="rf-1", label="Discrimination", severity="high"),
                ],
                prohibited_uses=[],
                required_documents=["Report"],
                compliance_questions=[
                    ComplianceQuestion(id="q-1", text="Q1", maps_to="rf-1"),
                ],
            )
        assert "too_short" in str(exc_info.value)

    def test_rejects_empty_compliance_questions(self):
        with pytest.raises(ValidationError) as exc_info:
            RegulationBody(
                name="EU AI Act",
                version="1.0",
                risk_factors=[
                    RiskFactor(id="rf-1", label="Discrimination", severity="high"),
                ],
                prohibited_uses=["Social scoring"],
                required_documents=["Report"],
                compliance_questions=[],
            )
        assert "too_short" in str(exc_info.value)

    def test_get_risk_factor_returns_correct_factor(self):
        body = RegulationBody(
            name="EU AI Act",
            version="1.0",
            risk_factors=[
                RiskFactor(id="rf-1", label="Discrimination", severity="high"),
                RiskFactor(id="rf-2", label="Safety Risk", severity="high"),
            ],
            prohibited_uses=["Social scoring"],
            required_documents=["Report"],
            compliance_questions=[
                ComplianceQuestion(id="q-1", text="Q1", maps_to="rf-1"),
            ],
        )
        found = body.get_risk_factor("rf-2")
        assert found is not None
        assert found.label == "Safety Risk"

    def test_get_risk_factor_returns_none_for_unknown_id(self):
        body = RegulationBody(
            name="EU AI Act",
            version="1.0",
            risk_factors=[
                RiskFactor(id="rf-1", label="Discrimination", severity="high"),
            ],
            prohibited_uses=["Social scoring"],
            required_documents=["Report"],
            compliance_questions=[
                ComplianceQuestion(id="q-1", text="Q1", maps_to="rf-1"),
            ],
        )
        assert body.get_risk_factor("rf-unknown") is None
