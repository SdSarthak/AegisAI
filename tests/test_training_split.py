"""Tests for deterministic training/validation splitting."""

from __future__ import annotations

from importlib import util
from pathlib import Path

import pandas as pd


def _load_split_module():
    module_path = Path(__file__).resolve().parents[1] / "backend" / "app" / "modules" / "guard" / "training" / "data" / "split.py"
    spec = util.spec_from_file_location("guard_training_split", module_path)
    module = util.module_from_spec(spec)
    assert spec and spec.loader
    spec.loader.exec_module(module)
    return module


def _make_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "prompt": [
                "alpha",
                "beta",
                "gamma",
                "delta",
                "epsilon",
                "zeta",
                "eta",
                "theta",
                "iota",
                "kappa",
            ],
            "label": [
                "benign",
                "malicious",
                "benign",
                "malicious",
                "benign",
                "malicious",
                "benign",
                "malicious",
                "benign",
                "malicious",
            ],
        }
    )


def test_train_validation_split_is_deterministic_for_same_seed() -> None:
    module = _load_split_module()
    frame = _make_frame()

    train_one, val_one = module.train_validation_split(frame, random_state=42)
    train_two, val_two = module.train_validation_split(frame, random_state=42)

    assert train_one["prompt"].tolist() == train_two["prompt"].tolist()
    assert val_one["prompt"].tolist() == val_two["prompt"].tolist()


def test_train_validation_split_changes_when_seed_changes() -> None:
    module = _load_split_module()
    frame = _make_frame()

    train_one, val_one = module.train_validation_split(frame, random_state=42)
    train_two, val_two = module.train_validation_split(frame, random_state=7)

    assert train_one["prompt"].tolist() != train_two["prompt"].tolist()
    assert val_one["prompt"].tolist() != val_two["prompt"].tolist()
