"""Evaluation helpers for guard classifier training."""

from .metrics import compute_classification_metrics

__all__ = [
    "EvaluationResult",
    "SafetyClassifierEvaluator",
    "compute_classification_metrics",
]


def __getattr__(name):
    """Lazily load evaluator classes because they depend on the model stack."""
    if name in {"EvaluationResult", "SafetyClassifierEvaluator"}:
        from .evaluator import EvaluationResult, SafetyClassifierEvaluator

        return {
            "EvaluationResult": EvaluationResult,
            "SafetyClassifierEvaluator": SafetyClassifierEvaluator,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
