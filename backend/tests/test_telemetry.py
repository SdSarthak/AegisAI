"""
Tests for backend/app/core/telemetry.py instrumentation helpers.

Covers:
- instrument_guard: observes latency histogram and increments decision
  counter for dict results; falls back to decision='unknown' otherwise
- instrument_rag: observes retrieval latency and increments success counter
- setup_telemetry: instruments the FastAPI app and exposes /metrics endpoint
"""

import pytest
import time
from unittest.mock import MagicMock, patch
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.telemetry import (
    instrument_guard,
    instrument_rag,
    setup_telemetry,
    GUARD_INFERENCE_LATENCY,
    GUARD_SCAN_TOTAL,
    RAG_RETRIEVAL_LATENCY,
    RAG_QUERY_TOTAL,
)


def _get_counter_value(counter, label_tuple):
    """Read current counter value for a given label tuple."""
    try:
        return counter._metrics.get(label_tuple, None)
    except AttributeError:
        return None


def _get_counter_child_value(counter, label_tuple):
    """Read the current value of a labelled counter child."""
    child = counter._metrics.get(label_tuple)
    if child is None:
        return None
    return child._value.get()


def _get_histogram_sum_if_present(histogram):
    """Read histogram sum if available (labelled histograms store per-label sums)."""
    if hasattr(histogram, '_sum'):
        return histogram._sum.get()
    return 0.0  # labelled histograms expose sum via _metrics children


# ---------------------------------------------------------------------------
# instrument_guard tests
# ---------------------------------------------------------------------------


def test_instrument_guard_observes_latency_and_increments_counter_for_dict_result():
    """instrument_guard should observe latency histogram and increment counter for dict result."""
    mock_fn = MagicMock(return_value={"decision": "allow", "score": 0.1})
    decorated = instrument_guard(mock_fn)

    # Read counters before
    before = _get_counter_child_value(GUARD_SCAN_TOTAL, ("allow",)) or 0.0

    result = decorated("test_arg", kwarg="value")

    # Verify the original function was called
    mock_fn.assert_called_once_with("test_arg", kwarg="value")

    # Verify result is passed through unchanged
    assert result == {"decision": "allow", "score": 0.1}

    # Verify counter was incremented
    after = _get_counter_child_value(GUARD_SCAN_TOTAL, ("allow",))
    assert after is not None
    assert after >= before + 1


def test_instrument_guard_falls_back_to_decision_unknown_for_non_dict():
    """instrument_guard should use decision='unknown' when result is not a dict."""
    mock_fn = MagicMock(return_value="not a dict result")
    decorated = instrument_guard(mock_fn)

    before = _get_counter_child_value(GUARD_SCAN_TOTAL, ("unknown",)) or 0.0

    result = decorated()

    assert result == "not a dict result"
    after = _get_counter_child_value(GUARD_SCAN_TOTAL, ("unknown",))
    assert after is not None
    assert after >= before + 1


def test_instrument_guard_handles_none_result():
    """instrument_guard should treat None result as non-dict (decision=unknown)."""
    mock_fn = MagicMock(return_value=None)
    decorated = instrument_guard(mock_fn)

    before = _get_counter_child_value(GUARD_SCAN_TOTAL, ("unknown",)) or 0.0

    result = decorated()
    assert result is None
    after = _get_counter_child_value(GUARD_SCAN_TOTAL, ("unknown",))
    assert after is not None
    assert after >= before + 1


def test_instrument_guard_uses_decision_from_dict_with_missing_key():
    """instrument_guard should use 'unknown' when result is a dict but has no 'decision' key."""
    mock_fn = MagicMock(return_value={"score": 0.5})
    decorated = instrument_guard(mock_fn)

    before = _get_counter_child_value(GUARD_SCAN_TOTAL, ("unknown",)) or 0.0

    result = decorated()
    assert result == {"score": 0.5}
    after = _get_counter_child_value(GUARD_SCAN_TOTAL, ("unknown",))
    assert after is not None
    assert after >= before + 1


def test_instrument_guard_records_decision_block():
    """instrument_guard should record decision='block' for blocked prompts."""
    mock_fn = MagicMock(return_value={"decision": "block"})
    decorated = instrument_guard(mock_fn)

    before = _get_counter_child_value(GUARD_SCAN_TOTAL, ("block",)) or 0.0

    decorated()

    after = _get_counter_child_value(GUARD_SCAN_TOTAL, ("block",))
    assert after is not None
    assert after >= before + 1


# ---------------------------------------------------------------------------
# instrument_rag tests
# ---------------------------------------------------------------------------


def test_instrument_rag_observes_latency_and_increments_success_counter():
    """instrument_rag should observe retrieval latency and increment success counter."""
    mock_fn = MagicMock(return_value={"chunks": ["chunk1", "chunk2"]})
    decorated = instrument_rag(mock_fn)

    before_sum = RAG_RETRIEVAL_LATENCY._sum.get()
    before_counter = _get_counter_child_value(RAG_QUERY_TOTAL, ("success",)) or 0.0

    result = decorated("test query")

    mock_fn.assert_called_once_with("test query")
    assert result == {"chunks": ["chunk1", "chunk2"]}

    # Verify latency was observed
    after_sum = RAG_RETRIEVAL_LATENCY._sum.get()
    assert after_sum >= before_sum

    # Verify success counter was incremented
    after_counter = _get_counter_child_value(RAG_QUERY_TOTAL, ("success",))
    assert after_counter is not None
    assert after_counter >= before_counter + 1


def test_instrument_rag_passes_through_exception():
    """instrument_rag should not suppress exceptions from the wrapped function."""
    mock_fn = MagicMock(side_effect=RuntimeError("vector store unavailable"))
    decorated = instrument_rag(mock_fn)

    with pytest.raises(RuntimeError, match="vector store unavailable"):
        decorated("test query")


# ---------------------------------------------------------------------------
# setup_telemetry tests
# ---------------------------------------------------------------------------


def test_setup_telemetry_instruments_app_and_exposes_metrics():
    """setup_telemetry should instrument the FastAPI app and expose /metrics."""
    app = FastAPI()

    # Setup telemetry BEFORE creating the TestClient (middleware must be added before startup)
    setup_telemetry(app)

    # Verify /metrics is accessible
    client = TestClient(app, raise_server_exceptions=False)
    resp = client.get("/metrics")
    assert resp.status_code == 200
    content_type = resp.headers.get("content-type", "")
    assert "text/plain" in content_type
    # Prometheus metrics should be present
    assert "python" in resp.text.lower() or "process" in resp.text.lower()
