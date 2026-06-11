"""Evaluation helpers for guard classifier training.

This package exposes the evaluation result types and metric helpers while
keeping the heavier model imports lazy until the evaluator is needed in a
pipeline or CLI invocation.
"""

from .metrics import compute_classification_metrics

__all__ = [
    "EvaluationResult",
    "SafetyClassifierEvaluator",
    "compute_classification_metrics",
]


def __getattr__(name):
    """Lazily load evaluator classes because they depend on the model stack.

    Args:
        name: Attribute requested from the package namespace.

    Returns:
        The lazily imported evaluation class or helper.
    """
    if name in {"EvaluationResult", "SafetyClassifierEvaluator"}:
        from .evaluator import EvaluationResult, SafetyClassifierEvaluator

        return {
            "EvaluationResult": EvaluationResult,
            "SafetyClassifierEvaluator": SafetyClassifierEvaluator,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
