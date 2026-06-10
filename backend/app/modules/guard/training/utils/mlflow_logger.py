"""Optional MLflow integration for guard training."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator


@contextmanager
def mlflow_run(enabled: bool, experiment_name: str, run_name: str) -> Iterator[object | None]:
    """Start an MLflow run when enabled, otherwise yield ``None``.

    Args:
        enabled: Whether MLflow logging should run.
        experiment_name: Target MLflow experiment name.
        run_name: MLflow run name.

    Yields:
        The active MLflow run object, or ``None`` when disabled.
    """
    if not enabled:
        yield None
        return

    import mlflow

    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name=run_name) as run:
        yield run


def log_metrics(metrics: dict, prefix: str = "") -> None:
    """Log numeric metrics to MLflow with an optional key prefix.

    Args:
        metrics: Dictionary of metrics to log.
        prefix: Optional prefix applied to every metric key.
    """
    import mlflow

    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            mlflow.log_metric(f"{prefix}{key}", value)
