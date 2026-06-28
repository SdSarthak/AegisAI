"""
Unit tests for backend/app/plugins/regulation_loader.py RegulationRegistry.

Covers: _load_file, get_regulation, list_regulations, init_registry,
get_registry, get_regulation, list_regulations.
"""

from __future__ import annotations

import pytest
import yaml
from pathlib import Path

from app.plugins.regulation_loader import (
    RegulationRegistry,
    init_registry,
    get_registry,
    get_regulation,
    list_regulations,
)


# ---------------------------------------------------------------------------
# Helpers to build valid RegulationFile YAML
# ---------------------------------------------------------------------------

def make_regulation_yaml(name: str, version: str, risk_factors: list, prohibited_uses: list,
                          required_documents: list, compliance_questions: list) -> dict:
    return {
        "regulation": {
            "name": name,
            "version": version,
            "risk_factors": risk_factors,
            "prohibited_uses": prohibited_uses,
            "required_documents": required_documents,
            "compliance_questions": compliance_questions,
        }
    }


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def valid_regulation_yaml(tmp_path: Path) -> Path:
    """Write a minimal valid regulation YAML file and return its path."""
    data = make_regulation_yaml(
        name="EU_AI_ACT",
        version="1.0",
        risk_factors=[{"id": "RF1", "label": "Risk Factor 1", "severity": "limited"}],
        prohibited_uses=["Unlawful discrimination"],
        required_documents=["Data governance policy"],
        compliance_questions=[{"id": "Q1", "text": "Is data quality managed?", "maps_to": "RF1"}],
    )
    filepath = tmp_path / "eu_ai_act.yaml"
    filepath.write_text(yaml.dump(data), encoding="utf-8")
    return filepath


@pytest.fixture
def invalid_regulation_yaml(tmp_path: Path) -> Path:
    """Write a regulation YAML missing the required 'regulation' key."""
    # Directly write invalid YAML (RegulationFile requires 'regulation' top-level key)
    filepath = tmp_path / "invalid.yaml"
    filepath.write_text("name: MissingRules\nversion: 1.0\n", encoding="utf-8")
    return filepath


@pytest.fixture
def builtin_dir(tmp_path: Path) -> Path:
    """Return a directory with one valid regulation."""
    reg_dir = tmp_path / "regulations"
    reg_dir.mkdir()
    data = make_regulation_yaml(
        name="TEST_REG",
        version="1.0",
        risk_factors=[{"id": "RF1", "label": "Test", "severity": "minimal"}],
        prohibited_uses=["Test prohibited use"],
        required_documents=["Test document"],
        compliance_questions=[{"id": "Q1", "text": "Test question?", "maps_to": "RF1"}],
    )
    (reg_dir / "test_reg.yaml").write_text(yaml.dump(data), encoding="utf-8")
    return reg_dir


@pytest.fixture
def custom_dir(tmp_path: Path) -> Path:
    """Return a directory with one custom regulation."""
    reg_dir = tmp_path / "custom"
    reg_dir.mkdir()
    data = make_regulation_yaml(
        name="CUSTOM_REG",
        version="2.0",
        risk_factors=[{"id": "RF1", "label": "Custom", "severity": "minimal"}],
        prohibited_uses=["Custom prohibited"],
        required_documents=["Custom doc"],
        compliance_questions=[{"id": "Q1", "text": "Custom question?", "maps_to": "RF1"}],
    )
    (reg_dir / "custom_reg.yaml").write_text(yaml.dump(data), encoding="utf-8")
    return reg_dir


# ---------------------------------------------------------------------------
# RegulationRegistry._load_file
# ---------------------------------------------------------------------------

class TestLoadFile:
    def test_load_file_returns_regulation_body(self, valid_regulation_yaml: Path):
        """A valid YAML file should parse into a RegulationBody."""
        registry = RegulationRegistry(builtin_dir=valid_regulation_yaml.parent)
        result = registry._load_file(valid_regulation_yaml)
        assert result.name == "EU_AI_ACT"
        assert result.version == "1.0"

    def test_load_file_raises_ValueError_on_invalid_yaml(self, invalid_regulation_yaml: Path, tmp_path: Path):
        """A YAML missing the 'regulation' key should raise ValueError wrapping ValidationError."""
        # Use an empty dir for init so _load_file is not called during __init__;
        # then call it directly on the invalid file.
        empty_dir = tmp_path / "empty"
        empty_dir.mkdir()
        registry = RegulationRegistry(builtin_dir=empty_dir)
        with pytest.raises(ValueError, match="validation errors"):
            registry._load_file(invalid_regulation_yaml)


# ---------------------------------------------------------------------------
# RegulationRegistry loading
# ---------------------------------------------------------------------------

class TestRegistryInit:
    def test_loads_builtin_regulations(self, builtin_dir: Path):
        """Registry should load all .yaml files from the builtin directory."""
        registry = RegulationRegistry(builtin_dir=builtin_dir)
        assert "TEST_REG" in registry.list_regulations()

    def test_custom_dir_overrides_builtin(self, tmp_path: Path):
        """A custom regulation with the same name should override the builtin one."""
        builtin_dir = tmp_path / "builtin"
        builtin_dir.mkdir()
        custom_dir = tmp_path / "custom"
        custom_dir.mkdir()

        builtin_data = make_regulation_yaml(
            name="OVERRIDE_ME",
            version="1.0",
            risk_factors=[{"id": "RF1", "label": "Builtin", "severity": "minimal"}],
            prohibited_uses=["Builtin prohibited"],
            required_documents=["Builtin doc"],
            compliance_questions=[{"id": "Q1", "text": "Builtin question?", "maps_to": "RF1"}],
        )
        custom_data = make_regulation_yaml(
            name="OVERRIDE_ME",
            version="2.0",
            risk_factors=[{"id": "RF1", "label": "Custom", "severity": "minimal"}],
            prohibited_uses=["Custom prohibited"],
            required_documents=["Custom doc"],
            compliance_questions=[{"id": "Q1", "text": "Custom question?", "maps_to": "RF1"}],
        )

        (builtin_dir / "override.yaml").write_text(yaml.dump(builtin_data), encoding="utf-8")
        (custom_dir / "override.yaml").write_text(yaml.dump(custom_data), encoding="utf-8")

        registry = RegulationRegistry(builtin_dir=builtin_dir, custom_dir=custom_dir)
        regulation = registry.get_regulation("OVERRIDE_ME")
        assert regulation.version == "2.0"

    def test_custom_dir_not_required(self, builtin_dir: Path):
        """Registry should work without a custom directory."""
        registry = RegulationRegistry(builtin_dir=builtin_dir)
        assert "TEST_REG" in registry.list_regulations()


# ---------------------------------------------------------------------------
# RegulationRegistry.get_regulation
# ---------------------------------------------------------------------------

class TestGetRegulation:
    def test_returns_correct_regulation(self, builtin_dir: Path):
        registry = RegulationRegistry(builtin_dir=builtin_dir)
        regulation = registry.get_regulation("TEST_REG")
        assert regulation.name == "TEST_REG"

    def test_raises_keyerror_for_unknown_regulation(self, builtin_dir: Path):
        registry = RegulationRegistry(builtin_dir=builtin_dir)
        with pytest.raises(KeyError, match="not found"):
            registry.get_regulation("NONEXISTENT")

    def test_keyerror_includes_available_regulations(self, builtin_dir: Path):
        registry = RegulationRegistry(builtin_dir=builtin_dir)
        with pytest.raises(KeyError, match="TEST_REG"):
            registry.get_regulation("NONEXISTENT")


# ---------------------------------------------------------------------------
# RegulationRegistry.list_regulations
# ---------------------------------------------------------------------------

class TestListRegulations:
    def test_returns_sorted_list(self, tmp_path: Path):
        """list_regulations should return names in sorted order."""
        reg_dir = tmp_path / "reg"
        reg_dir.mkdir()
        for name in ["ZEBRA", "APPLE", "BANANA"]:
            data = make_regulation_yaml(
                name=name,
                version="1.0",
                risk_factors=[{"id": "RF1", "label": name, "severity": "minimal"}],
                prohibited_uses=["Test"],
                required_documents=["Test doc"],
                compliance_questions=[{"id": "Q1", "text": "Test?", "maps_to": "RF1"}],
            )
            (reg_dir / f"{name.lower()}.yaml").write_text(yaml.dump(data), encoding="utf-8")
        registry = RegulationRegistry(builtin_dir=reg_dir)
        names = registry.list_regulations()
        assert names == sorted(names)


# ---------------------------------------------------------------------------
# Global helpers
# ---------------------------------------------------------------------------

class TestGlobalHelpers:
    def test_init_registry_sets_singleton(self, builtin_dir: Path):
        """init_registry should set the global registry."""
        init_registry(builtin_dir)
        registry = get_registry()
        assert isinstance(registry, RegulationRegistry)

    def test_get_registry_raises_when_not_initialized(self):
        """get_registry should raise RuntimeError before init_registry is called."""
        import app.plugins.regulation_loader as rl_module
        original = rl_module._registry
        rl_module._registry = None
        try:
            with pytest.raises(RuntimeError, match="init_registry"):
                get_registry()
        finally:
            rl_module._registry = original

    def test_get_regulation_global_raises_when_not_initialized(self):
        """Global get_regulation should raise RuntimeError before init."""
        import app.plugins.regulation_loader as rl_module
        original = rl_module._registry
        rl_module._registry = None
        try:
            with pytest.raises(RuntimeError, match="init_registry"):
                get_regulation("ANYTHING")
        finally:
            rl_module._registry = original

    def test_list_regulations_global_raises_when_not_initialized(self):
        """Global list_regulations should raise RuntimeError before init."""
        import app.plugins.regulation_loader as rl_module
        original = rl_module._registry
        rl_module._registry = None
        try:
            with pytest.raises(RuntimeError, match="init_registry"):
                list_regulations()
        finally:
            rl_module._registry = original
