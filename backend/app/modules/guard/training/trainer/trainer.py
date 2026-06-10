"""Expose a small trainer facade around the guard intent classifier.

The surrounding pipelines work with pandas dataframes, while the classifier
expects plain prompt and label lists. This facade bridges that gap and keeps
the higher-level pipeline code compact.
"""

from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from app.modules.guard.intent_classifier import IntentClassifier
from app.modules.guard.training.data.dataset_loader import resolve_backend_path


@dataclass
class TrainingResult:
    """Training outputs returned by the standardized trainer facade."""

    metrics: dict
    model_output_dir: Path


class SafetyClassifierTrainer:
    """Standardized wrapper around IntentClassifier.train.

    The trainer keeps the training entrypoint small and stable for the
    surrounding pipelines and scripts.
    """

    def __init__(self, model_output_dir: str | Path, device: str | None = None):
        """Initialize the trainer with an output directory and device choice.

        Args:
            model_output_dir: Directory where trained model artifacts are saved.
            device: Optional device override, or ``auto``/``None`` for default
                resolution.
        """
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
        """Train the classifier on the supplied datasets.

        Args:
            train_df: Training dataframe containing ``prompt`` and ``label``.
            val_df: Validation dataframe containing ``prompt`` and ``label``.
            epochs: Number of training epochs.
            batch_size: Mini-batch size.
            learning_rate: Optimizer learning rate.

        Returns:
            TrainingResult with model metrics and the output directory.
        """
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
