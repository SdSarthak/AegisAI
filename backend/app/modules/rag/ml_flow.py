"""Optional MLflow tracking helpers for RAG query runs.

The RAG pipeline can emit lightweight MLflow runs for offline analysis
without making MLflow a hard dependency for the rest of the backend.
"""

import logging

import mlflow

from app.core.config import settings

logger = logging.getLogger(__name__)


def log_query(
    question: str,
    answer: str,
    sources: list,
    latency_ms: float = 0.0,
) -> None:
    """Log a single RAG query as an MLflow run."""
    tracking_uri = settings.MLFLOW_TRACKING_URI or ""
    if tracking_uri:
        mlflow.set_tracking_uri(tracking_uri)

    try:
        with mlflow.start_run(run_name="rag_query"):
            # Parameters
            mlflow.log_param("question", question[:500])  # truncate to stay within MLflow limits

            # Metrics
            mlflow.log_metric("answer_length", len(answer))
            mlflow.log_metric("source_count", len(sources))
            mlflow.log_metric("response_latency_ms", latency_ms)

            # Artifact
            mlflow.log_text(answer, "answer.txt")
    except Exception as exc:
        # MLflow tracking is non-critical — log and continue
        logger.warning("MLflow logging failed: %s", exc)
