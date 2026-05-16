"""Evaluate an IntentClassifier on normalized prompt datasets."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from app.modules.guard.intent_classifier import IntentClassifier
from .metrics import compute_classification_metrics


@dataclass
class EvaluationResult:
    metrics: dict
    predictions: list[dict]


class SafetyClassifierEvaluator:
    """Batch evaluator for the prompt safety classifier."""

    def __init__(self, classifier: IntentClassifier):
        self.classifier = classifier

    def evaluate(self, df: pd.DataFrame) -> EvaluationResult:
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
