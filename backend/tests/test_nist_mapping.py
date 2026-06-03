"""Unit tests for NIST AI RMF mapping and document generation."""

import pytest

from app.modules.compliance.nist_mapping import (
    EU_TO_NIST_MAPPING,
    NIST_CORE_FUNCTIONS,
    NIST_AI_RMF_METADATA,
)
from app.modules.compliance.templates.nist_rmf_profile import (
    generate_nist_rmf_profile,
)


class TestNISTMapping:
    def test_all_eu_risk_tiers_have_mapping(self):
        for tier in ["MINIMAL", "LIMITED", "HIGH", "UNACCEPTABLE"]:
            assert tier in EU_TO_NIST_MAPPING

    def test_all_mappings_have_required_keys(self):
        required = {"primary_functions", "subcategories", "rationale", "nist_risk_tier"}
        for tier, mapping in EU_TO_NIST_MAPPING.items():
            assert required.issubset(mapping.keys()), f"{tier} missing keys"

    def test_high_risk_covers_all_four_functions(self):
        functions = EU_TO_NIST_MAPPING["HIGH"]["primary_functions"]
        assert set(functions) == {"GOVERN", "MAP", "MEASURE", "MANAGE"}

    def test_minimal_risk_only_govern(self):
        functions = EU_TO_NIST_MAPPING["MINIMAL"]["primary_functions"]
        assert functions == ["GOVERN"]

    def test_unacceptable_has_highest_nist_tier(self):
        tier = EU_TO_NIST_MAPPING["UNACCEPTABLE"]["nist_risk_tier"]
        assert tier == "Critical"

    def test_all_four_core_functions_defined(self):
        for fn in ["GOVERN", "MAP", "MEASURE", "MANAGE"]:
            assert fn in NIST_CORE_FUNCTIONS
            assert len(NIST_CORE_FUNCTIONS[fn]) > 10

    def test_metadata_has_required_fields(self):
        required = {"name", "version", "published", "publisher", "url"}
        assert required.issubset(NIST_AI_RMF_METADATA.keys())


class TestNISTProfileGeneration:
    def test_generates_markdown_for_high_risk(self):
        doc = generate_nist_rmf_profile(
            system_name="Test AI",
            system_description="A test AI system",
            eu_risk_level="HIGH",
        )
        assert "NIST AI RMF Profile" in doc
        assert "GOVERN" in doc
        assert "MEASURE" in doc
        assert "MANAGE" in doc

    def test_generates_for_all_risk_levels(self):
        for level in ["MINIMAL", "LIMITED", "HIGH", "UNACCEPTABLE"]:
            doc = generate_nist_rmf_profile(
                system_name="System",
                system_description="Description",
                eu_risk_level=level,
            )
            assert len(doc) > 100

    def test_system_name_appears_in_output(self):
        doc = generate_nist_rmf_profile(
            system_name="MyAISystem",
            system_description="test",
            eu_risk_level="LIMITED",
        )
        assert "MyAISystem" in doc

    def test_unknown_risk_level_returns_empty_gracefully(self):
        doc = generate_nist_rmf_profile(
            system_name="System",
            system_description="test",
            eu_risk_level="INVALID",
        )
        # Should not crash, just return minimal doc
        assert "NIST AI RMF Profile" in doc