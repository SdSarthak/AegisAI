"""
Unit tests for telemetry.py instrumentation decorators.
Run with: pytest tests/test_telemetry.py -v --noconftest
"""
import time
from unittest.mock import patch, MagicMock

import pytest

from app.core.telemetry import (
    instrument_guard,
    instrument_rag,
    GUARD_INFERENCE_LATENCY,
    GUARD_SCAN_TOTAL,
    RAG_RETRIEVAL_LATENCY,
    RAG_QUERY_TOTAL,
)


class TestInstrumentGuard:
    """Tests for instrument_guard decorator."""

    def test_calls_wrapped_function_and_passes_return_value(self):
        """Decorator must call the original function and return its result."""
        @instrument_guard
        def sample_fn(x: int) -> int:
            return x * 2

        assert sample_fn(5) == 10

    def test_records_latency_histogram(self):
        """Decorator must observe elapsed time in GUARD_INFERENCE_LATENCY."""
        @instrument_guard
        def sample_fn() -> dict:
            time.sleep(0.01)
            return {"decision": "allow"}

        with patch.object(GUARD_INFERENCE_LATENCY, "labels") as mock_labels:
            mock_hist = MagicMock()
            mock_labels.return_value = mock_hist
            sample_fn()

            mock_labels.assert_called_once_with(decision="allow")
            mock_hist.observe.assert_called_once()
            obs_arg = mock_hist.observe.call_args[0][0]
            assert obs_arg >= 0.01

    def test_increments_decision_counter(self):
        """Decorator must increment GUARD_SCAN_TOTAL for the given decision."""
        @instrument_guard
        def sample_fn() -> dict:
            return {"decision": "block"}

        with patch.object(GUARD_SCAN_TOTAL, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter
            sample_fn()

            mock_labels.assert_called_once_with(decision="block")
            mock_counter.inc.assert_called_once()

    def test_reads_decision_from_result_dict(self):
        """instrument_guard reads decision from result.get('decision')."""
        @instrument_guard
        def sample_fn() -> dict:
            return {"decision": "sanitize"}

        with patch.object(GUARD_SCAN_TOTAL, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter
            sample_fn()

            mock_labels.assert_called_with(decision="sanitize")

    def test_returns_unknown_decision_for_non_dict(self):
        """When result is not a dict, decision defaults to 'unknown'."""
        @instrument_guard
        def sample_fn() -> str:
            return "not a dict"

        with patch.object(GUARD_SCAN_TOTAL, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter
            sample_fn()

            mock_labels.assert_called_with(decision="unknown")

    def test_decorator_preserves_function_metadata(self):
        """@wraps preserves __name__ and __doc__."""
        @instrument_guard
        def documented_fn() -> int:
            """Docstring here."""
            return 42

        assert documented_fn.__name__ == "documented_fn"
        assert documented_fn.__doc__ == "Docstring here."


class TestInstrumentRag:
    """Tests for instrument_rag decorator."""

    def test_calls_wrapped_function_and_passes_return_value(self):
        """Decorator must call the original function and return its result."""
        @instrument_rag
        def sample_fn(x: str) -> str:
            return f"processed: {x}"

        assert sample_fn("hello") == "processed: hello"

    def test_records_retrieval_latency(self):
        """Decorator must observe elapsed time in RAG_RETRIEVAL_LATENCY."""
        @instrument_rag
        def sample_fn() -> str:
            time.sleep(0.01)
            return "result"

        with patch.object(RAG_RETRIEVAL_LATENCY, "observe") as mock_observe:
            sample_fn()

            assert mock_observe.call_count == 1
            obs_arg = mock_observe.call_args[0][0]
            assert obs_arg >= 0.01

    def test_increments_rag_query_counter_on_success(self):
        """Decorator must increment RAG_QUERY_TOTAL with status=success."""
        @instrument_rag
        def sample_fn() -> str:
            return "success result"

        with patch.object(RAG_QUERY_TOTAL, "labels") as mock_labels:
            mock_counter = MagicMock()
            mock_labels.return_value = mock_counter
            sample_fn()

            mock_labels.assert_called_with(status="success")
            mock_counter.inc.assert_called_once()

    def test_decorator_preserves_function_metadata(self):
        """@wraps preserves __name__ and __doc__."""
        @instrument_rag
        def documented_fn() -> int:
            """RAG docstring."""
            return 99

        assert documented_fn.__name__ == "documented_fn"
        assert documented_fn.__doc__ == "RAG docstring."
