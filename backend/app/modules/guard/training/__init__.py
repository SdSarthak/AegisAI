"""Standardized training pipeline for the guard safety classifier."""

__all__ = ["run_training_pipeline", "run_evaluation_pipeline"]


def __getattr__(name):
    if name == "run_training_pipeline":
        from .pipelines.train_pipeline import run_training_pipeline

        return run_training_pipeline
    if name == "run_evaluation_pipeline":
        from .pipelines.evaluate_pipeline import run_evaluation_pipeline

        return run_evaluation_pipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
