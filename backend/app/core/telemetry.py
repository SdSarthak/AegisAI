"""OpenTelemetry + Prometheus instrumentation for observability.

Exposes:
  - FastAPI request latency histograms (via prometheus-fastapi-instrumentator)
  - Guard inference pipeline latency & counters
  - RAG retrieval latency
  - SQLAlchemy query duration
  - /metrics endpoint (Prometheus scrape target)
"""

from __future__ import annotations

import time
from functools import wraps
from typing import Any, Callable, TypeVar

from prometheus_client import Counter, Histogram, Gauge
from prometheus_fastapi_instrumentator import Instrumentator

_F = TypeVar("_F", bound=Callable[..., Any])

# ---------------------------------------------------------------------------
# Custom Prometheus Metrics
# ---------------------------------------------------------------------------

GUARD_INFERENCE_LATENCY = Histogram(
    "aegisai_guard_inference_duration_seconds",
    "Guard inference pipeline latency in seconds",
    ["decision"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

GUARD_SCAN_TOTAL = Counter(
    "aegisai_guard_scans_total",
    "Total number of guard scans performed",
    ["decision"],
)

GUARD_BATCH_SIZE = Histogram(
    "aegisai_guard_batch_size",
    "Number of prompts per batch scan",
    buckets=(1, 2, 5, 10, 20, 50),
)

RAG_RETRIEVAL_LATENCY = Histogram(
    "aegisai_rag_retrieval_duration_seconds",
    "RAG retrieval latency in seconds",
    buckets=(0.1, 0.5, 1, 2.5, 5, 10, 30),
)

RAG_QUERY_TOTAL = Counter(
    "aegisai_rag_queries_total",
    "Total number of RAG queries",
    ["status"],
)

DB_QUERY_LATENCY = Histogram(
    "aegisai_db_query_duration_seconds",
    "Database query latency in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1),
)

AI_SYSTEMS_TOTAL = Gauge(
    "aegisai_ai_systems_total",
    "Total number of AI systems registered in the platform",
)


def get_total_systems() -> float:
    try:
        from app.core.database import SessionLocal
        from app.models import AISystem
        db = SessionLocal()
        try:
            return float(db.query(AISystem).count())
        finally:
            db.close()
    except Exception:
        return 0.0


AI_SYSTEMS_TOTAL.set_function(get_total_systems)

# ---------------------------------------------------------------------------
# FastAPI Instrumentator — auto-instruments HTTP request latencies / counts
# ---------------------------------------------------------------------------

instrumentator = Instrumentator(
    should_group_status_codes=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=[
        "/metrics",
        "/health",
        "/ready",
        "/docs",
        "/redoc",
        "/openapi.json",
    ],
    inprogress_name="aegisai_http_requests_active",
    inprogress_labels=True,
)


# ---------------------------------------------------------------------------
# Decorator helpers
# ---------------------------------------------------------------------------


def instrument_guard(fn: _F) -> _F:
    """Time guard inference and record decision counters."""

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        duration = time.perf_counter() - start
        decision = (
            result.get("decision", "unknown")
            if isinstance(result, dict)
            else "unknown"
        )
        GUARD_INFERENCE_LATENCY.labels(decision=decision).observe(duration)
        GUARD_SCAN_TOTAL.labels(decision=decision).inc()
        return result

    return wrapper  # type: ignore[return-value]


def instrument_rag(fn: _F) -> _F:
    """Time RAG retrieval calls."""

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        start = time.perf_counter()
        result = fn(*args, **kwargs)
        duration = time.perf_counter() - start
        RAG_RETRIEVAL_LATENCY.observe(duration)
        RAG_QUERY_TOTAL.labels(status="success").inc()
        return result

    return wrapper  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Initialisation
# ---------------------------------------------------------------------------


def setup_telemetry(app: Any) -> None:
    """Initialise all observability instrumentation on the FastAPI app."""
    from prometheus_fastapi_instrumentator import metrics
    instrumentator.add(metrics.default(metric_namespace="aegisai"))
    instrumentator.instrument(app).expose(app, endpoint="/metrics")
