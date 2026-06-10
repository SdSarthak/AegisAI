"""Trainer facade for guard safety prediction models.

This package exposes the standardized training entrypoint while keeping the
heavy classifier imports lazy until the trainer is actually requested.
"""

__all__ = ["SafetyClassifierTrainer", "TrainingResult"]


def __getattr__(name):
    """Lazily load trainer classes because they initialize classifier dependencies.

    Args:
        name: Attribute requested from the package namespace.

    Returns:
        The lazily imported trainer class or result dataclass.
    """
    if name in {"SafetyClassifierTrainer", "TrainingResult"}:
        from .trainer import SafetyClassifierTrainer, TrainingResult

        return {
            "SafetyClassifierTrainer": SafetyClassifierTrainer,
            "TrainingResult": TrainingResult,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
