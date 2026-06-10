"""Evaluate the guard classifier on normalized prompt datasets.

This module turns dataframe rows into classifier calls, collects per-row
predictions, and aggregates the results into JSON-serializable metrics for
pipeline artifacts.
"""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.modules.guard.intent_classifier import IntentClassifier
from .metrics import compute_classification_metrics


@dataclass
class EvaluationResult:
    """Evaluation outputs returned by the classifier evaluator."""

    metrics: dict
    predictions: list[dict]


class SafetyClassifierEvaluator:
    """Batch evaluator for the prompt safety classifier.

    The evaluator runs the classifier over a dataframe and returns both
    aggregate metrics and per-row predictions.
    """

    def __init__(self, classifier: IntentClassifier):
        """Store the classifier instance used during evaluation."""
        self.classifier = classifier

    def evaluate(self, df: pd.DataFrame) -> EvaluationResult:
        """Evaluate the classifier on a dataframe of prompts.

        Args:
            df: Dataframe containing ``prompt`` and ``label`` columns.

        Returns:
            EvaluationResult with aggregate metrics and row-level predictions.
        """
        predictions = []
        predicted_labels = []

        for row in df.itertuples(index=False):
            result = self.classifier.classify(row.prompt)
            predicted_labels.append(result.intent)
            predictions.append(
                {
                    "prompt": row.prompt,
                    "label": row.label,
                    "prediction": result.intent,
                    "confidence": result.confidence,
                    "class_scores": result.class_scores,
                }
            )

        metrics = compute_classification_metrics(df["label"].tolist(), predicted_labels)
        return EvaluationResult(metrics=metrics, predictions=predictions)
