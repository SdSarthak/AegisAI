"""Normalize raw datasets into the guard classifier's expected schema.

The training pipeline accepts a variety of source datasets, so this module
standardizes text and label columns, drops unusable rows, and maps label
variants back to the canonical guard classes.
"""

from typing import Iterable

import pandas as pd

LABEL_MAP = {
    0: "benign",
    1: "malicious",
    "0": "benign",
    "1": "malicious",
    "safe": "benign",
    "benign": "benign",
    "clean": "benign",
    "injection": "malicious",
    "prompt_injection": "malicious",
    "malicious": "malicious",
    "unsafe": "malicious",
    "suspicious": "suspicious",
}


def normalize_training_frame(
    df: pd.DataFrame,
    text_column: str = "prompt",
    label_column: str = "label",
    valid_labels: Iterable[str] | None = ("benign", "suspicious", "malicious"),
) -> pd.DataFrame:
    """Return a clean DataFrame with standardized prompt and label columns.

    Args:
        df: Raw training dataframe.
        text_column: Name of the text column to normalize.
        label_column: Name of the label column to normalize.
        valid_labels: Optional iterable of allowed label values.

    Returns:
        A normalized dataframe with ``prompt`` and ``label`` columns.
    """
    working = df.copy()
    valid_labels = tuple(valid_labels or ("benign", "suspicious", "malicious"))

    if text_column not in working.columns and "text" in working.columns:
        working = working.rename(columns={"text": text_column})

    if text_column not in working.columns or label_column not in working.columns:
        raise ValueError(
            "Dataset must contain text and label columns. "
            f"Got columns: {working.columns.tolist()}"
        )

    valid_label_set = set(valid_labels)
    working = working[[text_column, label_column]].dropna()
    working[text_column] = working[text_column].astype(str).str.strip()
    working[label_column] = working[label_column].map(
        lambda value: LABEL_MAP.get(value, LABEL_MAP.get(str(value).strip().lower(), value))
    )
    working[label_column] = working[label_column].astype(str).str.strip().str.lower()
    working = working[working[text_column] != ""]
    working = working[working[label_column].isin(valid_label_set)]
    working = working.drop_duplicates(subset=[text_column]).reset_index(drop=True)

    return working.rename(columns={text_column: "prompt", label_column: "label"})
