import logging
from pathlib import Path

import yaml
from app.plugins.schema import RegulationBody, RegulationFile
from pydantic import ValidationError

logger = logging.getLogger(__name__)


class RegulationRegistry:
    def __init__(self, builtin_dir: Path, custom_dir: Path | None = None) -> None:
        self.builtin_dir = builtin_dir
        self.custom_dir = custom_dir
        self._registry: dict[str, RegulationBody] = {}
        self._load_all()

    def _load_all(self) -> None:
        self._load_dir(self.builtin_dir, is_custom=False)

        if self.custom_dir is not None and self.custom_dir.exists():
            self._load_dir(self.custom_dir, is_custom=True)

    def _load_dir(self, directory: Path, *, is_custom: bool) -> None:
        for filepath in sorted(directory.glob("*.yaml")):
            regulation = self._load_file(filepath)
            if is_custom and regulation.name in self._registry:
                logger.warning(
                    "Custom regulation ruleset %s overrides built-in regulation %s",
                    filepath,
                    regulation.name,
                )
            self._registry[regulation.name] = regulation

    def _load_file(self, filepath: Path) -> RegulationBody:
        try:
            raw_data = yaml.safe_load(filepath.read_text(encoding="utf-8"))
            return RegulationFile.model_validate(raw_data).regulation
        except ValidationError as exc:
            raise ValueError(f"[{filepath.name}] {exc}") from exc

    def get_regulation(self, name: str) -> RegulationBody:
        try:
            return self._registry[name]
        except KeyError as exc:
            available = ", ".join(self.list_regulations()) or "none"
            raise KeyError(
                f"Regulation '{name}' not found. Available regulations: {available}"
            ) from exc

    def list_regulations(self) -> list[str]:
        return sorted(self._registry)


_registry: RegulationRegistry | None = None


def init_registry(builtin_dir: Path, custom_dir: Path | None = None) -> RegulationRegistry:
    global _registry
    _registry = RegulationRegistry(builtin_dir, custom_dir)
    return _registry


def get_registry() -> RegulationRegistry:
    """Return the module-level registry singleton for use by route handlers."""
    if _registry is None:
        raise RuntimeError(
            "Regulation registry not initialized. Call init_registry() first."
        )
    return _registry


def get_regulation(name: str) -> RegulationBody:
    if _registry is None:
        raise RuntimeError(
            "Regulation registry not initialized. Call init_registry() first."
        )
    return _registry.get_regulation(name)


def list_regulations() -> list[str]:
    if _registry is None:
        raise RuntimeError(
            "Regulation registry not initialized. Call init_registry() first."
        )
    return _registry.list_regulations()
