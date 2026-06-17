"""Deterministic dataset splitting helpers."""

from __future__ import annotations

import pandas as pd

try:
    from sklearn.model_selection import train_test_split
except ImportError:
    train_test_split = None


def train_validation_split(
    df: pd.DataFrame,
    test_size: float = 0.2,
    random_state: int = 42,
    stratify: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Split a normalized training frame into train and validation frames."""
    if train_test_split is None:
        return _fallback_train_validation_split(
            df=df,
            test_size=test_size,
            random_state=random_state,
            stratify=stratify,
        )

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


def _fallback_train_validation_split(
    df: pd.DataFrame,
    test_size: float,
    random_state: int,
    stratify: bool,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Deterministically split a frame without sklearn."""
    if df.empty:
        return df.copy(), df.copy()

    rng = __import__("random").Random(random_state)
    validation_indices: list[int] = []

    if stratify and "label" in df and df["label"].nunique() > 1:
        for _, group in df.groupby("label"):
            indices = list(group.index)
            rng.shuffle(indices)
            val_count = max(1, int(round(len(indices) * test_size)))
            validation_indices.extend(indices[:val_count])
    else:
        indices = list(df.index)
        rng.shuffle(indices)
        val_count = max(1, int(round(len(indices) * test_size)))
        validation_indices = indices[:val_count]

    validation_set = set(validation_indices)
    train_df = df.loc[[idx for idx in df.index if idx not in validation_set]]
    val_df = df.loc[[idx for idx in df.index if idx in validation_set]]
    return train_df.reset_index(drop=True), val_df.reset_index(drop=True)
