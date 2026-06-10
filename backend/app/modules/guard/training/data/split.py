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
    """Split a normalized training frame into train and validation frames.

    Args:
        df: Normalized training dataframe with a ``label`` column.
        test_size: Fraction of rows reserved for validation.
        random_state: Seed used for deterministic splitting.
        stratify: Whether to stratify on the label column when possible.

    Returns:
        A tuple of ``(train_df, val_df)`` with reset indexes.
    """
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
