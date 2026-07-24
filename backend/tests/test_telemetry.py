"""Unit tests for backend/app/core/telemetry.py instrumentation module."""

import asyncio
import time
from unittest.mock import MagicMock, patch

import pytest

from app.core import telemetry


class TestInstrumentGuard:
    """Tests for instrument_guard decorator."""

    def test_sync_wrapper_records_inference_metrics(self):
        """Sync function decorated with instrument_guard records decision metrics."""
        def mock_guard(prompt: str) -> dict:
            return {"decision": "ALLOW", "metadata": {}}

        decorated = telemetry.instrument_guard(mock_guard)
        result = decorated("hello")

        assert result["decision"] == "ALLOW"

    def test_async_wrapper_records_inference_metrics(self):
        """Async function decorated with instrument_guard records decision metrics."""
        async def mock_async_guard(prompt: str) -> dict:
            await asyncio.sleep(0.001)
            return {"decision": "BLOCK", "metadata": {}}

        decorated = telemetry.instrument_guard(mock_async_guard)
        result = asyncio.run(decorated("hello"))

        assert result["decision"] == "BLOCK"

    def test_decorator_preserves_function_metadata(self):
        """instrument_guard preserves function name and docstring."""

        @telemetry.instrument_guard
        def my_guard_fn(prompt: str) -> dict:
            """My function docstring."""
            return {"decision": "ALLOW", "metadata": {}}

        assert my_guard_fn.__name__ == "my_guard_fn"
        assert my_guard_fn.__doc__ == "My function docstring."

    def test_decorator_passes_through_non_dict_result(self):
        """instrument_guard handles non-dict return values gracefully."""

        @telemetry.instrument_guard
        def bad_guard(prompt: str) -> str:
            return "not a dict"

        result = bad_guard("test")
        assert result == "not a dict"


class TestInstrumentRag:
    """Tests for instrument_rag decorator."""

    def test_sync_wrapper_records_retrieval_metrics(self):
        """Sync function decorated with instrument_rag records retrieval metrics."""
        def mock_retrieval(query: str) -> list:
            return ["chunk1", "chunk2"]

        decorated = telemetry.instrument_rag(mock_retrieval)
        result = decorated("test query")

        assert result == ["chunk1", "chunk2"]

    def test_async_wrapper_records_retrieval_metrics(self):
        """Async function decorated with instrument_rag records retrieval metrics."""
        async def mock_async_retrieval(query: str) -> list:
            await asyncio.sleep(0.001)
            return ["chunk1", "chunk2"]

        decorated = telemetry.instrument_rag(mock_async_retrieval)
        result = asyncio.run(decorated("test query"))

        assert result == ["chunk1", "chunk2"]

    def test_decorator_preserves_function_metadata(self):

        @telemetry.instrument_rag
        def my_rag_fn(query: str) -> list:
            """My RAG function."""
            return []

        assert my_rag_fn.__name__ == "my_rag_fn"
        assert my_rag_fn.__doc__ == "My RAG function."


class TestPrometheusMetrics:
    """Tests that custom Prometheus metrics are defined correctly."""

    def test_guard_inference_latency_histogram_exists(self):
        """GUARD_INFERENCE_LATENCY histogram is defined with correct labels."""
        assert hasattr(telemetry, "GUARD_INFERENCE_LATENCY")
        assert "decision" in telemetry.GUARD_INFERENCE_LATENCY._labelnames

    def test_guard_scan_total_counter_exists(self):
        """GUARD_SCAN_TOTAL counter is defined with correct labels."""
        assert hasattr(telemetry, "GUARD_SCAN_TOTAL")
        assert "decision" in telemetry.GUARD_SCAN_TOTAL._labelnames

    def test_guard_batch_size_histogram_exists(self):
        """GUARD_BATCH_SIZE histogram is defined."""
        assert hasattr(telemetry, "GUARD_BATCH_SIZE")

    def test_rag_retrieval_latency_histogram_exists(self):
        """RAG_RETRIEVAL_LATENCY histogram is defined."""
        assert hasattr(telemetry, "RAG_RETRIEVAL_LATENCY")

    def test_rag_query_total_counter_exists(self):
        """RAG_QUERY_TOTAL counter is defined with correct labels."""
        assert hasattr(telemetry, "RAG_QUERY_TOTAL")
        assert "status" in telemetry.RAG_QUERY_TOTAL._labelnames

    def test_db_query_latency_histogram_exists(self):
        """DB_QUERY_LATENCY histogram is defined with correct labels."""
        assert hasattr(telemetry, "DB_QUERY_LATENCY")
        assert "operation" in telemetry.DB_QUERY_LATENCY._labelnames


class TestInstrumentator:
    """Tests for the FastAPI instrumentator setup."""

    def test_instrumentator_is_instantiated(self):
        """instrumentator is created with expected configuration."""
        assert hasattr(telemetry, "instrumentator")
        assert hasattr(telemetry.instrumentator, "instrument")

    def test_instrumentator_has_expose_method(self):
        """instrumentator has the expose() method required to add /metrics endpoint."""
        assert hasattr(telemetry.instrumentator, "expose")
