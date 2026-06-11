"""Persist lightweight training artifacts in a backend-relative location.

The guard training pipeline writes small JSON summaries alongside model
artifacts so runs can be inspected after the fact without depending on a
database or object store. These helpers resolve paths relative to the
backend root, create parent directories on demand, and keep the JSON output
stable for deterministic diffs in CI.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.modules.guard.training.data.dataset_loader import resolve_backend_path


def utc_run_id(prefix: str = "run") -> str:
    """Return a UTC-stamped identifier that is safe for filenames."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{timestamp}"


def save_json_artifact(data: dict[str, Any], output_path: str | Path) -> Path:
    """Serialize ``data`` to JSON and return the resolved artifact path."""
    path = resolve_backend_path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return path


def save_predictions(predictions: list[dict[str, Any]], output_path: str | Path) -> Path:
    """Wrap prediction rows in a standard payload before persisting them."""
    return save_json_artifact({"predictions": predictions}, output_path)
