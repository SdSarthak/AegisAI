"""Prometheus instrumentation helpers for the AegisAI backend.

This module centralizes the metrics used across the API so endpoints,
guard inference, RAG retrieval, and database queries all report into the
same Prometheus namespace. Keeping the counters and histograms in one place
also makes it easier to wire the /metrics endpoint into FastAPI with a
single setup function.
"""

import time
from functools import wraps
from typing import Any, Callable, TypeVar

from prometheus_client import Counter, Histogram
from prometheus_fastapi_instrumentator import Instrumentator

_F = TypeVar("_F", bound=Callable[..., Any])

# ---------------------------------------------------------------------------
# Custom Prometheus Metrics
# ---------------------------------------------------------------------------

GUARD_INFERENCE_LATENCY = Histogram(
    "aegis_guard_inference_duration_seconds",
    "Guard inference pipeline latency in seconds",
    ["decision"],
    buckets=(0.01, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10),
)

GUARD_SCAN_TOTAL = Counter(
    "aegis_guard_scans_total",
    "Total number of guard scans performed",
    ["decision"],
)

GUARD_BATCH_SIZE = Histogram(
    "aegis_guard_batch_size",
    "Number of prompts per batch scan",
    buckets=(1, 2, 5, 10, 20, 50),
)

RAG_RETRIEVAL_LATENCY = Histogram(
    "aegis_rag_retrieval_duration_seconds",
    "RAG retrieval latency in seconds",
    buckets=(0.1, 0.5, 1, 2.5, 5, 10, 30),
)

RAG_QUERY_TOTAL = Counter(
    "aegis_rag_queries_total",
    "Total number of RAG queries",
    ["status"],
)

DB_QUERY_LATENCY = Histogram(
    "aegis_db_query_duration_seconds",
    "Database query latency in seconds",
    ["operation"],
    buckets=(0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1),
)

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
    inprogress_name="aegis_http_requests_active",
    inprogress_labels=True,
)


# ---------------------------------------------------------------------------
# Decorator helpers
# ---------------------------------------------------------------------------


def instrument_guard(fn: _F) -> _F:
    """Wrap guard inference and record latency plus decision metrics."""

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
    """Wrap RAG retrieval calls with latency and success counters."""

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
    """Attach request metrics and expose the Prometheus scrape endpoint."""
    instrumentator.instrument(app).expose(app, endpoint="/metrics")
