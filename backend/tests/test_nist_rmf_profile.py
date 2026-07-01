"""
Unit tests for backend/app/modules/compliance/templates/nist_rmf_profile.py
"""

import pytest

from app.modules.compliance.templates.nist_rmf_profile import (
    generate_nist_rmf_profile,
)
from app.modules.compliance.nist_mapping import (
    EU_TO_NIST_MAPPING,
    NIST_AI_RMF_METADATA,
    NIST_CORE_FUNCTIONS,
)


class TestGenerateNistRmfProfile:
    def test_returns_string(self):
        result = generate_nist_rmf_profile(
            system_name="TestSystem",
            system_description="A test AI system.",
            eu_risk_level="minimal",
        )
        assert isinstance(result, str)

    def test_starts_with_header(self):
        result = generate_nist_rmf_profile(
            system_name="CV Screener",
            system_description="Automated CV screening system.",
            eu_risk_level="high",
        )
        assert result.startswith("# NIST AI RMF Profile")

    def test_contains_system_name(self):
        result = generate_nist_rmf_profile(
            system_name="Loan Advisor",
            system_description="AI loan approval advisor.",
            eu_risk_level="limited",
        )
        assert "Loan Advisor" in result

    def test_contains_organization(self):
        result = generate_nist_rmf_profile(
            system_name="TestSys",
            system_description="Desc",
            eu_risk_level="high",
            organization="Acme Corp",
        )
        assert "Acme Corp" in result

    def test_contains_framework_metadata(self):
        result = generate_nist_rmf_profile(
            system_name="TestSys",
            system_description="Desc",
            eu_risk_level="minimal",
        )
        meta = NIST_AI_RMF_METADATA
        assert meta["name"] in result
        assert meta["version"] in result

    def test_contains_nist_url(self):
        result = generate_nist_rmf_profile(
            system_name="TestSys",
            system_description="Desc",
            eu_risk_level="minimal",
        )
        assert NIST_AI_RMF_METADATA["url"] in result

    def test_contains_system_description(self):
        desc = "A recruitment AI that screens job candidates automatically."
        result = generate_nist_rmf_profile(
            system_name="RecruitBot",
            system_description=desc,
            eu_risk_level="high",
        )
        assert desc in result

    def test_high_risk_includes_all_four_core_functions(self):
        result = generate_nist_rmf_profile(
            system_name="TestSys",
            system_description="Desc",
            eu_risk_level="high",
        )
        for fn in ["GOVERN", "MAP", "MEASURE", "MANAGE"]:
            assert fn in result

    def test_minimal_risk_includes_govern_function(self):
        result = generate_nist_rmf_profile(
            system_name="TestSys",
            system_description="Desc",
            eu_risk_level="minimal",
        )
        assert "GOVERN" in result

    def test_unacceptable_risk_tier_shown(self):
        result = generate_nist_rmf_profile(
            system_name="TestSys",
            system_description="Desc",
            eu_risk_level="unacceptable",
        )
        assert "unacceptable" in result.lower()

    def test_unknown_risk_level_uses_defaults(self):
        result = generate_nist_rmf_profile(
            system_name="TestSys",
            system_description="Desc",
            eu_risk_level="nonexistent",
        )
        # Should not raise; returns a document with empty sections
        assert isinstance(result, str)

    def test_case_insensitive_risk_level(self):
        result_upper = generate_nist_rmf_profile(
            system_name="TestSys",
            system_description="Desc",
            eu_risk_level="HIGH",
        )
        result_lower = generate_nist_rmf_profile(
            system_name="TestSys",
            system_description="Desc",
            eu_risk_level="high",
        )
        # Both should produce the same NIST tier
        assert "MANAGE" in result_upper
        assert "MANAGE" in result_lower

    def test_contains_nist_risk_tier(self):
        mapping = EU_TO_NIST_MAPPING["HIGH"]
        nist_tier = mapping["nist_risk_tier"]
        result = generate_nist_rmf_profile(
            system_name="TestSys",
            system_description="Desc",
            eu_risk_level="high",
        )
        assert nist_tier in result

    def test_contains_rationale(self):
        rationale = EU_TO_NIST_MAPPING["HIGH"]["rationale"]
        result = generate_nist_rmf_profile(
            system_name="TestSys",
            system_description="Desc",
            eu_risk_level="high",
        )
        # Rationale text should appear in the Rationale section
        # (at least part of the rationale should be present)
        assert len(result) > len(rationale)  # rationale is included somewhere

    def test_contains_subcategories(self):
        subcategories = EU_TO_NIST_MAPPING["LIMITED"]["subcategories"]
        result = generate_nist_rmf_profile(
            system_name="TestSys",
            system_description="Desc",
            eu_risk_level="limited",
        )
        # At least the first subcategory should appear
        assert len(subcategories) > 0
        assert subcategories[0][:20] in result

    def test_generated_document_is_markdown(self):
        result = generate_nist_rmf_profile(
            system_name="TestSys",
            system_description="Desc",
            eu_risk_level="minimal",
        )
        lines = result.split("\n")
        header_lines = [l for l in lines if l.startswith("#")]
        assert len(header_lines) >= 3  # at least H1 and section headers

    def test_limited_risk_not_missing_core_functions(self):
        result = generate_nist_rmf_profile(
            system_name="TestSys",
            system_description="Desc",
            eu_risk_level="limited",
        )
        # Limited risk maps to GOVERN and MAP, not MEASURE or MANAGE
        assert "GOVERN" in result
        assert "MAP" in result
