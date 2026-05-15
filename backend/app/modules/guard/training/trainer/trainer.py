"""Trainer facade for the guard intent classifier."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.modules.guard.intent_classifier import IntentClassifier
from app.modules.guard.training.data.dataset_loader import resolve_backend_path


@dataclass
class TrainingResult:
    metrics: dict
    model_output_dir: Path


class SafetyClassifierTrainer:
    """Standardized wrapper around IntentClassifier.train."""

    def __init__(self, model_output_dir: str | Path, device: str | None = None):
        self.model_output_dir = resolve_backend_path(model_output_dir)
        self.device = None if device in (None, "auto") else device

    def train(
        self,
        train_df: pd.DataFrame,
        val_df: pd.DataFrame,
        epochs: int = 3,
        batch_size: int = 16,
        learning_rate: float = 2e-5,
    ) -> TrainingResult:
        classifier = IntentClassifier(device=self.device)
        metrics = classifier.train(
            train_texts=train_df["prompt"].tolist(),
            train_labels=train_df["label"].tolist(),
            val_texts=val_df["prompt"].tolist(),
            val_labels=val_df["label"].tolist(),
            epochs=epochs,
            batch_size=batch_size,
            learning_rate=learning_rate,
            output_dir=str(self.model_output_dir),
        )
        return TrainingResult(metrics=metrics, model_output_dir=self.model_output_dir)
