"""Load and persist training datasets for the guard classifier."""

from __future__ import annotations

from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from app.modules.guard import guard_config as config
from .preprocess import normalize_training_frame


DEFAULT_HF_DATASET = "xTRam1/safe-guard-prompt-injection"


def resolve_backend_path(path: str | Path) -> Path:
    """Resolve relative config paths from the backend directory."""
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
    """Load and normalize a local CSV dataset."""
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
    """Download and normalize a Hugging Face dataset split."""
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
    """Load a local dataset unless a fresh Hugging Face download is requested."""
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
