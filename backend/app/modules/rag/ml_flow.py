"""
MLflow tracking helpers for RAG queries.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

Each call to log_query() opens a new MLflow run and records:
  - Params : question text
  - Metrics: answer_length (chars), source_count, response_latency_ms
  - Artifact: answer text saved as answer.txt

To view the MLflow UI locally:
  1. Set MLFLOW_TRACKING_URI in backend/.env (see .env.example).
     Leave it empty to use the default local ./mlruns directory.
  2. Run:  mlflow ui --port 5001
  3. Open: http://localhost:5001
"""

import logging
import os

import mlflow

logger = logging.getLogger(__name__)


def log_query(
    question: str,
    answer: str,
    sources: list,
    latency_ms: float = 0.0,
) -> None:
    """
    Log a single RAG query as an MLflow run.

    Args:
        question:    The user's question text.
        answer:      The generated answer text.
        sources:     List of source document identifiers used to ground the answer.
        latency_ms:  End-to-end response latency in milliseconds.
    """
    tracking_uri = os.getenv("MLFLOW_TRACKING_URI", "")
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

def log_query(question: str, answer: str, sources: list):
    with mlflow.start_run():
        mlflow.log_param("question", question)
        mlflow.log_metric("source_count", len(sources))
        mlflow.log_text(answer, "answer.txt")
