"""Deterministic dataset splitting helpers."""

from __future__ import annotations

import pandas as pd
from sklearn.model_selection import train_test_split


def train_validation_split(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42,
    stratify: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a normalized training frame into train and validation frames."""
    stratify_values = df["label"] if stratify and df["label"].nunique() > 1 else None
    try:
        train_df, val_df = train_test_split(
            df,
            test_size=test_size,
            random_state=random_state,
            stratify=stratify_values,
        )
    except ValueError:
        train_df, val_df = train_test_split(
            df,
            test_size=test_size,
            random_state=random_state,
            stratify=None,
        )
    return train_df.reset_index(drop=True), val_df.reset_index(drop=True)
