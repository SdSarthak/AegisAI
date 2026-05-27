"""Regression tests for deterministic training/validation splits."""

import pandas as pd

from app.modules.guard.training.data.split import train_validation_split


def _make_training_frame() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "text": [
                "sample 1",
                "sample 2",
                "sample 3",
                "sample 4",
                "sample 5",
                "sample 6",
                "sample 7",
                "sample 8",
                "sample 9",
                "sample 10",
            ],
            "label": [0, 1, 0, 1, 0, 1, 0, 1, 0, 1],
        }
    )


def test_train_validation_split_is_deterministic_for_same_seed():
    frame = _make_training_frame()

    first_train, first_val = train_validation_split(frame, random_state=42)
    second_train, second_val = train_validation_split(frame, random_state=42)

    assert first_train.equals(second_train)
    assert first_val.equals(second_val)


def test_train_validation_split_changes_with_different_seed():
    frame = _make_training_frame()

    first_train, first_val = train_validation_split(frame, random_state=42)
    second_train, second_val = train_validation_split(frame, random_state=7)

    assert not first_train.equals(second_train) or not first_val.equals(second_val)