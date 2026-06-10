"""Metrics for safety classifier evaluation."""

from __future__ import annotations

from typing import Iterable

from sklearn.metrics import accuracy_score, classification_report, f1_score


def compute_classification_metrics(
    true_labels: Iterable[str],
    predicted_labels: Iterable[str],
) -> dict:
    """Compute common classification metrics as JSON-serializable values.

    Args:
        true_labels: Ground-truth labels.
        predicted_labels: Predicted labels from the classifier.

    Returns:
        A JSON-serializable metrics dictionary.
    """
    y_true = list(true_labels)
    y_pred = list(predicted_labels)
    return {
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "weighted_f1": float(f1_score(y_true, y_pred, average="weighted", zero_division=0)),
        "macro_f1": float(f1_score(y_true, y_pred, average="macro", zero_division=0)),
        "classification_report": classification_report(
            y_true,
            y_pred,
            output_dict=True,
            zero_division=0,
        ),
    }
