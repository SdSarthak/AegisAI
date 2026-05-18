"""Optional MLflow integration for guard training."""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator


@contextmanager
def mlflow_run(enabled: bool, experiment_name: str, run_name: str) -> Iterator[object | None]:
    """Start an MLflow run when enabled, otherwise yield None."""
    if not enabled:
        yield None
        return

    import mlflow

    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name=run_name) as run:
        yield run


def log_metrics(metrics: dict, prefix: str = "") -> None:
    import mlflow

    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            mlflow.log_metric(f"{prefix}{key}", value)
