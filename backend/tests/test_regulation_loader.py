from pathlib import Path

import pytest

from app.plugins import regulation_loader
from app.plugins.regulation_loader import RegulationRegistry
from app.plugins.schema import RegulationBody


BUILTIN_REGULATIONS = Path(__file__).resolve().parent.parent / "regulations"


@pytest.fixture(autouse=True)
def reset_registry() -> None:
    regulation_loader._registry = None


def _write_valid_ruleset(
    directory: Path,
    *,
    name: str = "Example Act",
    version: str = "1",
    severity: str = "high",
    extra_line: str = "",
    omit_prohibited_uses: bool = False,
) -> Path:
    directory.mkdir(parents=True, exist_ok=True)
    prohibited_uses = (
        ""
        if omit_prohibited_uses
        else '  prohibited_uses:\n    - "Example prohibited use"\n'
    )
    filepath = directory / "ruleset.yaml"
    filepath.write_text(
        f"""regulation:
  name: "{name}"
  version: "{version}"
  risk_factors:
    - id: "example_risk"
      label: "Example risk"
      severity: "{severity}"
{prohibited_uses}  required_documents:
    - "Example document"
  compliance_questions:
    - id: "q1"
      text: "Example question?"
      maps_to: "example_risk"
{extra_line}""",
        encoding="utf-8",
    )
    return filepath


def test_valid_yaml_loads() -> None:
    registry = RegulationRegistry(BUILTIN_REGULATIONS)

    regulation = registry.get_regulation("EU AI Act")
    risk_factor_ids = {risk_factor.id for risk_factor in regulation.risk_factors}

    assert regulation.name == "EU AI Act"
    assert regulation.risk_factors
    assert all(
        question.maps_to in risk_factor_ids
        for question in regulation.compliance_questions
    )


def test_list_regulations() -> None:
    regulation_loader.init_registry(BUILTIN_REGULATIONS)

    assert "EU AI Act" in regulation_loader.list_regulations()


def test_get_regulation_returns_correct_object() -> None:
    regulation_loader.init_registry(BUILTIN_REGULATIONS)

    regulation = regulation_loader.get_regulation("EU AI Act")

    assert isinstance(regulation, RegulationBody)
    assert regulation.name == "EU AI Act"


def test_get_regulation_unknown_raises() -> None:
    regulation_loader.init_registry(BUILTIN_REGULATIONS)

    with pytest.raises(KeyError):
        regulation_loader.get_regulation("Nonexistent Act")


def test_missing_required_field_raises(tmp_path: Path) -> None:
    _write_valid_ruleset(tmp_path, omit_prohibited_uses=True)

    with pytest.raises(ValueError):
        RegulationRegistry(tmp_path)


def test_unknown_key_raises(tmp_path: Path) -> None:
    _write_valid_ruleset(tmp_path, extra_line="  banana: true\n")

    with pytest.raises(ValueError):
        RegulationRegistry(tmp_path)


def test_invalid_severity_raises(tmp_path: Path) -> None:
    _write_valid_ruleset(tmp_path, severity="extreme")

    with pytest.raises(ValueError):
        RegulationRegistry(tmp_path)


def test_invalid_maps_to_reference_raises(tmp_path: Path) -> None:
    _write_valid_ruleset(
        tmp_path,
        extra_line=(
            '    - id: "q2"\n'
            '      text: "Broken mapping?"\n'
            '      maps_to: "missing_risk"\n'
        ),
    )

    with pytest.raises(ValueError):
        RegulationRegistry(tmp_path)


def test_custom_dir_overrides_builtin(tmp_path: Path) -> None:
    builtin_dir = tmp_path / "builtin"
    custom_dir = tmp_path / "custom"
    _write_valid_ruleset(builtin_dir, name="EU AI Act", version="2024")
    _write_valid_ruleset(custom_dir, name="EU AI Act", version="OVERRIDE")

    registry = RegulationRegistry(builtin_dir, custom_dir)

    assert registry.get_regulation("EU AI Act").version == "OVERRIDE"


def test_uninitialized_registry_raises() -> None:
    with pytest.raises(RuntimeError):
        regulation_loader.get_regulation("EU AI Act")


def test_get_registry_uninitialized_raises() -> None:
    """get_registry() must raise RuntimeError when the module-level registry is None."""
    with pytest.raises(RuntimeError, match="not initialized"):
        regulation_loader.get_registry()


def test_list_regulations_uninitialized_raises() -> None:
    """list_regulations() must raise RuntimeError when the module-level registry is None."""
    with pytest.raises(RuntimeError, match="not initialized"):
        regulation_loader.list_regulations()
