"""Executable training and evaluation pipelines for the guard classifier."""

__all__ = [
    "load_training_config",
    "run_evaluation_pipeline",
    "run_training_pipeline",
]


def __getattr__(name):
    """Lazily expose pipeline entry points without eager model imports."""
    if name in {"load_training_config", "run_training_pipeline"}:
        from .train_pipeline import load_training_config, run_training_pipeline

        return {
            "load_training_config": load_training_config,
            "run_training_pipeline": run_training_pipeline,
        }[name]
    if name == "run_evaluation_pipeline":
        from .evaluate_pipeline import run_evaluation_pipeline

        return run_evaluation_pipeline
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
