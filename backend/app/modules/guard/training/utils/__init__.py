"""Utility helpers shared across the guard training pipelines.

This namespace collects the small support functions used by training and
evaluation jobs while leaving heavier dependencies lazily imported until a
run actually needs them.
"""

from .checkpoint import save_json_artifact, save_predictions, utc_run_id
from .logger import get_training_logger

__all__ = [
    "get_training_logger",
    "log_metrics",
    "mlflow_run",
    "save_json_artifact",
    "save_predictions",
    "set_seed",
    "utc_run_id",
]


def __getattr__(name):
    """Load optional or heavier utility dependencies only when requested.

    Args:
        name: Attribute name requested from the module namespace.

    Returns:
        The lazily imported utility function.

    Raises:
        AttributeError: If the requested attribute does not exist.
    """
    if name == "set_seed":
        from .seed import set_seed

        return set_seed
    if name in {"log_metrics", "mlflow_run"}:
        from .mlflow_logger import log_metrics, mlflow_run

        return {"log_metrics": log_metrics, "mlflow_run": mlflow_run}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
