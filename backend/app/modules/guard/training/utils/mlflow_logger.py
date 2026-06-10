"""Optional MLflow helpers for guard training runs.

These helpers keep experiment logging optional so the training pipeline can
run cleanly whether or not MLflow is installed or configured.
"""

from __future__ import annotations

from contextlib import contextmanager
from typing import Iterator


@contextmanager
def mlflow_run(enabled: bool, experiment_name: str, run_name: str) -> Iterator[object | None]:
    """Start an MLflow run when enabled, otherwise yield ``None``."""
    if not enabled:
        yield None
        return

    import mlflow

    mlflow.set_experiment(experiment_name)
    with mlflow.start_run(run_name=run_name) as run:
        yield run


def log_metrics(metrics: dict, prefix: str = "") -> None:
    """Log numeric metrics to MLflow with an optional key prefix."""
    import mlflow

    for key, value in metrics.items():
        if isinstance(value, (int, float)):
            mlflow.log_metric(f"{prefix}{key}", value)
