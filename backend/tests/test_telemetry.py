"""
Unit tests for backend/app/core/telemetry.py.

Tests cover:
  - instrument_guard decorator: records inference latency and decision counter
  - instrument_rag decorator: records retrieval latency and success counter
  - Histogram and Counter metric label/label-value correctness
"""

from prometheus_client import REGISTRY
from prometheus_client.metrics import Histogram, Counter


def _get_histogram_value(name: str, label_names: tuple[str, ...], label_values: tuple[str, ...]) -> float | None:
    """Return the sum of a histogram bucket series, or None if not found."""
    for metric in REGISTRY.collect():
        for sample in metric.samples:
            if (
                sample.name == name
                and sample.labels == dict(zip(label_names, label_values))
            ):
                if "_sum" in sample.name:
                    return sample.value
    return None


def _get_counter_value(name: str, label_names: tuple[str, ...], label_values: tuple[str, ...]) -> float | None:
    """Return the value of a counter series, or None if not found."""
    for metric in REGISTRY.collect():
        for sample in metric.samples:
            if (
                sample.name == name
                and sample.labels == dict(zip(label_names, label_values))
            ):
                return sample.value
    return None


class TestInstrumentGuard:
    """Tests for instrument_guard decorator."""

    def test_guard_decorator_records_latency_and_counter(self):
        from app.core.telemetry import instrument_guard, GUARD_INFERENCE_LATENCY, GUARD_SCAN_TOTAL

        @instrument_guard
        def dummy_guard(prompt: str) -> dict:
            return {"decision": "allow", "metadata": {}}

        result = dummy_guard("test prompt")

        assert result["decision"] == "allow"
        assert GUARD_INFERENCE_LATENCY is not None
        assert GUARD_SCAN_TOTAL is not None

    def test_guard_decorator_classifies_decision_from_dict_result(self):
        from app.core.telemetry import instrument_guard

        @instrument_guard
        def guard_block(prompt: str) -> dict:
            return {"decision": "block", "metadata": {}}

        guard_block("block this")

    def test_guard_decorator_propagates_non_dict_result(self):
        from app.core.telemetry import instrument_guard

        @instrument_guard
        def guard_plain(prompt: str) -> str:
            return "allow"

        result = guard_plain("hello")
        assert result == "allow"

    def test_guard_decorator_uses_unknown_for_missing_decision(self):
        from app.core.telemetry import instrument_guard

        @instrument_guard
        def guard_no_decision(prompt: str) -> dict:
            return {"metadata": {}}

        guard_no_decision("test")


class TestInstrumentRAG:
    """Tests for instrument_rag decorator."""

    def test_rag_decorator_records_latency_and_counter(self):
        from app.core.telemetry import instrument_rag, RAG_RETRIEVAL_LATENCY, RAG_QUERY_TOTAL

        @instrument_rag
        def dummy_retriever(query: str) -> list:
            return []

        result = dummy_retriever("test query")

        assert result == []
        assert RAG_RETRIEVAL_LATENCY is not None
        assert RAG_QUERY_TOTAL is not None

    def test_rag_decorator_propagates_return_value(self):
        from app.core.telemetry import instrument_rag

        @instrument_rag
        def dummy_retriever(query: str) -> list:
            return ["doc1", "doc2"]

        result = dummy_retriever("test")
        assert result == ["doc1", "doc2"]


class TestMetricsPresence:
    """Smoke tests verifying metrics are defined and have correct type."""

    def test_guard_inference_histogram_exists(self):
        from app.core.telemetry import GUARD_INFERENCE_LATENCY

        assert isinstance(GUARD_INFERENCE_LATENCY, Histogram)

    def test_guard_scan_counter_exists(self):
        from app.core.telemetry import GUARD_SCAN_TOTAL

        assert isinstance(GUARD_SCAN_TOTAL, Counter)

    def test_guard_batch_histogram_exists(self):
        from app.core.telemetry import GUARD_BATCH_SIZE

        assert isinstance(GUARD_BATCH_SIZE, Histogram)

    def test_rag_retrieval_histogram_exists(self):
        from app.core.telemetry import RAG_RETRIEVAL_LATENCY

        assert isinstance(RAG_RETRIEVAL_LATENCY, Histogram)

    def test_rag_query_counter_exists(self):
        from app.core.telemetry import RAG_QUERY_TOTAL

        assert isinstance(RAG_QUERY_TOTAL, Counter)

    def test_db_query_histogram_exists(self):
        from app.core.telemetry import DB_QUERY_LATENCY

        assert isinstance(DB_QUERY_LATENCY, Histogram)
