"""Artifact persistence utilities for training and evaluation runs."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.modules.guard.training.data.dataset_loader import resolve_backend_path


def utc_run_id(prefix: str = "run") -> str:
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    return f"{prefix}-{timestamp}"


def save_json_artifact(data: dict[str, Any], output_path: str | Path) -> Path:
    path = resolve_backend_path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, sort_keys=True), encoding="utf-8")
    return path


def save_predictions(predictions: list[dict[str, Any]], output_path: str | Path) -> Path:
    return save_json_artifact({"predictions": predictions}, output_path)
