"""Load and persist training datasets for the guard classifier."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from app.modules.guard import guard_config as config
from .preprocess import normalize_training_frame


DEFAULT_HF_DATASET = "xTRam1/safe-guard-prompt-injection"


def resolve_backend_path(path: str | Path) -> Path:
    """Resolve relative config paths from the backend directory.

    Args:
        path: Absolute or backend-relative path.

    Returns:
        An absolute Path rooted at the backend directory when needed.
    """
    path = Path(path)
    if path.is_absolute():
        return path
    return config.BACKEND_ROOT / path


def load_local_dataset(
    csv_path: str | Path,
    text_column: str = "prompt",
    label_column: str = "label",
    valid_labels: Iterable[str] = ("benign", "suspicious", "malicious"),
) -> pd.DataFrame:
    """Load and normalize a local CSV dataset.

    Args:
        csv_path: Path to the local CSV file.
        text_column: Column containing the prompt text.
        label_column: Column containing the label values.
        valid_labels: Allowed label values for the dataset.

    Returns:
        A normalized pandas DataFrame ready for training.
    """
    return normalize_training_frame(
        pd.read_csv(resolve_backend_path(csv_path)),
        text_column=text_column,
        label_column=label_column,
        valid_labels=valid_labels,
    )


def download_huggingface_dataset(
    dataset_name: str = DEFAULT_HF_DATASET,
    split: str = "train",
    text_column: str = "prompt",
    label_column: str = "label",
    valid_labels: Iterable[str] = ("benign", "suspicious", "malicious"),
) -> pd.DataFrame:
    """Download and normalize a Hugging Face dataset split.

    Args:
        dataset_name: Hugging Face dataset name.
        split: Dataset split to load.
        text_column: Column containing the prompt text.
        label_column: Column containing the label values.
        valid_labels: Allowed label values for the dataset.

    Returns:
        A normalized pandas DataFrame ready for training.

    Raises:
        ValueError: If the requested split does not exist.
    """
    from datasets import load_dataset

    dataset = load_dataset(dataset_name)
    if split not in dataset:
        raise ValueError(f"Dataset '{dataset_name}' does not include split '{split}'.")
    return normalize_training_frame(
        dataset[split].to_pandas(),
        text_column=text_column,
        label_column=label_column,
        valid_labels=valid_labels,
    )


def load_or_download_dataset(
    local_csv_path: str | Path,
    dataset_name: str = DEFAULT_HF_DATASET,
    force_download: bool = False,
    text_column: str = "prompt",
    label_column: str = "label",
    valid_labels: Optional[Iterable[str]] = None,
) -> pd.DataFrame:
    """Load a local dataset unless a fresh Hugging Face download is requested.

    Args:
        local_csv_path: Local cache path for the CSV dataset.
        dataset_name: Hugging Face dataset name.
        force_download: When True, bypass the local cache.
        text_column: Column containing the prompt text.
        label_column: Column containing the label values.
        valid_labels: Optional label whitelist.

    Returns:
        A normalized pandas DataFrame, cached locally when downloaded.
    """
    valid_labels = tuple(valid_labels or ("benign", "suspicious", "malicious"))
    local_path = resolve_backend_path(local_csv_path)

    if local_path.exists() and not force_download:
        return load_local_dataset(local_path, text_column, label_column, valid_labels)

    df = download_huggingface_dataset(
        dataset_name=dataset_name,
        text_column=text_column,
        label_column=label_column,
        valid_labels=valid_labels,
    )
    local_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(local_path, index=False)
    return df
