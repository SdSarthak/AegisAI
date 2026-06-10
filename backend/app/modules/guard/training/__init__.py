"""Standardized training namespace for the guard safety classifier.

The package exposes the training and evaluation pipeline entrypoints while
keeping heavyweight imports deferred until they are actually used.
"""

__all__ = ["run_training_pipeline", "run_evaluation_pipeline"]


def __getattr__(name):
    if name == "run_training_pipeline":
        from .pipelines.train_pipeline import run_training_pipeline

        return run_training_pipeline
    if name == "run_evaluation_pipeline":
        from .pipelines.evaluate_pipeline import run_evaluation_pipeline

        return run_evaluation_pipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
