"""Trainer facade for guard safety prediction models."""

__all__ = ["SafetyClassifierTrainer", "TrainingResult"]


def __getattr__(name):
    """Lazily load trainer classes because they initialize classifier dependencies."""
    if name in {"SafetyClassifierTrainer", "TrainingResult"}:
        from .trainer import SafetyClassifierTrainer, TrainingResult

        return {
            "SafetyClassifierTrainer": SafetyClassifierTrainer,
            "TrainingResult": TrainingResult,
        }[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
