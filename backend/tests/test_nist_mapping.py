"""
Unit tests for backend/app/modules/compliance/nist_mapping.py.
"""

import pytest

from app.modules.compliance.nist_mapping import (
    EU_TO_NIST_MAPPING,
    NIST_AI_RMF_METADATA,
    NIST_CORE_FUNCTIONS,
)


class TestEUMapping:
    """Tests for EU_TO_NIST_MAPPING."""

    @pytest.mark.parametrize("risk_tier", ["MINIMAL", "LIMITED", "HIGH", "UNACCEPTABLE"])
    def test_all_tiers_have_required_keys(self, risk_tier):
        entry = EU_TO_NIST_MAPPING[risk_tier]
        assert "primary_functions" in entry
        assert "subcategories" in entry
        assert "rationale" in entry
        assert "nist_risk_tier" in entry

    @pytest.mark.parametrize("risk_tier", ["MINIMAL", "LIMITED", "HIGH", "UNACCEPTABLE"])
    def test_primary_functions_is_list(self, risk_tier):
        funcs = EU_TO_NIST_MAPPING[risk_tier]["primary_functions"]
        assert isinstance(funcs, list)
        assert len(funcs) > 0
        assert all(isinstance(f, str) for f in funcs)

    @pytest.mark.parametrize("risk_tier", ["MINIMAL", "LIMITED", "HIGH", "UNACCEPTABLE"])
    def test_subcategories_is_list(self, risk_tier):
        subs = EU_TO_NIST_MAPPING[risk_tier]["subcategories"]
        assert isinstance(subs, list)
        assert len(subs) > 0
        assert all(isinstance(s, str) for s in subs)

    def test_high_risk_has_all_four_core_functions(self):
        funcs = set(EU_TO_NIST_MAPPING["HIGH"]["primary_functions"])
        assert funcs == {"GOVERN", "MAP", "MEASURE", "MANAGE"}

    def test_minimal_risk_has_only_govern(self):
        funcs = set(EU_TO_NIST_MAPPING["MINIMAL"]["primary_functions"])
        assert funcs == {"GOVERN"}

    def test_nist_risk_tier_is_nonempty_string(self):
        for tier in EU_TO_NIST_MAPPING:
            tier_str = EU_TO_NIST_MAPPING[tier]["nist_risk_tier"]
            assert isinstance(tier_str, str)
            assert len(tier_str) > 0


class TestNISTCoreFunctions:
    """Tests for NIST_CORE_FUNCTIONS."""

    def test_all_core_functions_present(self):
        assert set(NIST_CORE_FUNCTIONS.keys()) == {"GOVERN", "MAP", "MEASURE", "MANAGE"}

    @pytest.mark.parametrize("func", ["GOVERN", "MAP", "MEASURE", "MANAGE"])
    def test_descriptions_are_nonempty(self, func):
        desc = NIST_CORE_FUNCTIONS[func]
        assert isinstance(desc, str)
        assert len(desc) > 20


class TestNISTMetadata:
    """Tests for NIST_AI_RMF_METADATA."""

    def test_metadata_has_required_fields(self):
        assert "name" in NIST_AI_RMF_METADATA
        assert "version" in NIST_AI_RMF_METADATA
        assert "publisher" in NIST_AI_RMF_METADATA
        assert "url" in NIST_AI_RMF_METADATA

    def test_url_is_valid_format(self):
        url = NIST_AI_RMF_METADATA["url"]
        assert url.startswith("https://")
        assert "nist" in url.lower()
