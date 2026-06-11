"""Data loading, preprocessing, and splitting helpers for guard training.

The data package wraps the steps needed to fetch, normalize, and partition
training data into the shapes expected by the guard training pipeline and
keeps the source dataset handling in one predictable place.
"""

from .dataset_loader import (
    DEFAULT_HF_DATASET,
    download_huggingface_dataset,
    load_local_dataset,
    load_or_download_dataset,
    resolve_backend_path,
)
from .preprocess import LABEL_MAP, normalize_training_frame
from .split import train_validation_split

__all__ = [
    "DEFAULT_HF_DATASET",
    "LABEL_MAP",
    "download_huggingface_dataset",
    "load_local_dataset",
    "load_or_download_dataset",
    "normalize_training_frame",
    "resolve_backend_path",
    "train_validation_split",
]
