"""
Unit tests for backend/app/plugins/schema.py
RegulationBody, RegulationFile, RiskFactor, and ComplianceQuestion schemas.
"""

import pytest
from pydantic import ValidationError

from app.plugins.schema import (
    RegulationBody,
    RegulationFile,
    RiskFactor,
    ComplianceQuestion,
    SeverityEnum,
)


class TestRiskFactor:
    def test_valid_risk_factor(self):
        rf = RiskFactor(id="hr_recruitment", label="HR Recruitment", severity="high")
        assert rf.id == "hr_recruitment"
        assert rf.label == "HR Recruitment"
        assert rf.severity == "high"

    def test_rejects_invalid_severity(self):
        with pytest.raises(ValidationError) as exc_info:
            RiskFactor(id="x", label="X", severity="invalid")
        assert "severity" in str(exc_info.value)


class TestComplianceQuestion:
    def test_valid_compliance_question(self):
        cq = ComplianceQuestion(id="q1", text="Is training data documented?", maps_to="hr_recruitment")
        assert cq.id == "q1"
        assert cq.maps_to == "hr_recruitment"

    def test_maps_to_can_be_any_string(self):
        cq = ComplianceQuestion(id="q1", text="Q?", maps_to="any_factor_id")
        assert cq.maps_to == "any_factor_id"


class TestRegulationBody:
    def test_valid_minimal_regulation(self):
        body = RegulationBody(
            name="EU AI Act",
            version="1.0",
            risk_factors=[
                RiskFactor(id="rf1", label="RF1", severity="minimal"),
            ],
            prohibited_uses=["Prohibited system X"],
            compliance_questions=[
                ComplianceQuestion(id="q1", text="Q?", maps_to="rf1"),
            ],
        )
        assert body.name == "EU AI Act"
        assert len(body.risk_factors) == 1

    def test_rejects_empty_risk_factors(self):
        with pytest.raises(ValidationError) as exc_info:
            RegulationBody(
                name="Test",
                version="1.0",
                risk_factors=[],
                prohibited_uses=["use"],
                compliance_questions=[ComplianceQuestion(id="q1", text="?", maps_to="rf1")],
            )
        assert "risk_factors" in str(exc_info.value)

    def test_rejects_empty_prohibited_uses(self):
        with pytest.raises(ValidationError) as exc_info:
            RegulationBody(
                name="Test",
                version="1.0",
                risk_factors=[RiskFactor(id="rf1", label="RF1", severity="high")],
                prohibited_uses=[],
                compliance_questions=[ComplianceQuestion(id="q1", text="?", maps_to="rf1")],
            )
        assert "prohibited_uses" in str(exc_info.value)

    def test_rejects_empty_compliance_questions(self):
        with pytest.raises(ValidationError) as exc_info:
            RegulationBody(
                name="Test",
                version="1.0",
                risk_factors=[RiskFactor(id="rf1", label="RF1", severity="high")],
                prohibited_uses=["use"],
                compliance_questions=[],
            )
        assert "compliance_questions" in str(exc_info.value)

    def test_rejects_invalid_maps_to_reference(self):
        with pytest.raises(ValidationError) as exc_info:
            RegulationBody(
                name="Test",
                version="1.0",
                risk_factors=[RiskFactor(id="rf1", label="RF1", severity="high")],
                prohibited_uses=["use"],
                compliance_questions=[
                    ComplianceQuestion(id="q1", text="Q?", maps_to="nonexistent_id"),
                ],
            )
        assert "maps_to" in str(exc_info.value).lower()

    def test_accepts_valid_maps_to_reference(self):
        body = RegulationBody(
            name="Test",
            version="1.0",
            risk_factors=[
                RiskFactor(id="rf1", label="RF1", severity="high"),
                RiskFactor(id="rf2", label="RF2", severity="minimal"),
            ],
            prohibited_uses=["use"],
            compliance_questions=[
                ComplianceQuestion(id="q1", text="Q1?", maps_to="rf1"),
                ComplianceQuestion(id="q2", text="Q2?", maps_to="rf2"),
            ],
        )
        assert body.compliance_questions[0].maps_to == "rf1"

    def test_get_risk_factor_returns_match(self):
        body = RegulationBody(
            name="Test",
            version="1.0",
            risk_factors=[RiskFactor(id="rf1", label="RF1", severity="high")],
            prohibited_uses=["use"],
            compliance_questions=[ComplianceQuestion(id="q1", text="?", maps_to="rf1")],
        )
        rf = body.get_risk_factor("rf1")
        assert rf is not None
        assert rf.id == "rf1"

    def test_get_risk_factor_returns_none_for_missing(self):
        body = RegulationBody(
            name="Test",
            version="1.0",
            risk_factors=[RiskFactor(id="rf1", label="RF1", severity="high")],
            prohibited_uses=["use"],
            compliance_questions=[ComplianceQuestion(id="q1", text="?", maps_to="rf1")],
        )
        rf = body.get_risk_factor("nonexistent")
        assert rf is None

    def test_extra_fields_forbidden(self):
        with pytest.raises(ValidationError):
            RegulationBody(
                name="Test",
                version="1.0",
                risk_factors=[RiskFactor(id="rf1", label="RF1", severity="high")],
                prohibited_uses=["use"],
                compliance_questions=[ComplianceQuestion(id="q1", text="?", maps_to="rf1")],
                unknown_field="should fail",
            )


class TestRegulationFile:
    def test_valid_regulation_file(self):
        file = RegulationFile(
            regulation=RegulationBody(
                name="EU AI Act",
                version="1.0",
                risk_factors=[RiskFactor(id="rf1", label="RF1", severity="high")],
                prohibited_uses=["use"],
                compliance_questions=[ComplianceQuestion(id="q1", text="?", maps_to="rf1")],
            )
        )
        assert file.regulation.name == "EU AI Act"

    def test_extra_fields_forbidden_in_file(self):
        with pytest.raises(ValidationError):
            RegulationFile(
                regulation=RegulationBody(
                    name="EU AI Act",
                    version="1.0",
                    risk_factors=[RiskFactor(id="rf1", label="RF1", severity="high")],
                    prohibited_uses=["use"],
                    compliance_questions=[ComplianceQuestion(id="q1", text="?", maps_to="rf1")],
                ),
                extra_field="should fail",
            )

    def test_severity_enum_values(self):
        for sev in ["prohibited", "high", "limited", "minimal"]:
            rf = RiskFactor(id="x", label="X", severity=sev)
            assert rf.severity == sev
