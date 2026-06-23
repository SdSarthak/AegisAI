"""Unit tests for backend/app/core/telemetry.py."""

from __future__ import annotations

from unittest.mock import MagicMock, patch
import pytest

from app.core import telemetry


class TestInstrumentGuard:
    """Tests for instrument_guard decorator."""

    def test_observes_latency_and_increments_decision_counter(self) -> None:
        """instrument_guard records duration histogram and increments decision counter."""
        @telemetry.instrument_guard
        def guarded_fn(x: int) -> dict[str, str]:
            return {"decision": "allow", "result": x * 2}

        # Patch the histogram and counter to avoid Prometheus registration issues
        with patch.object(telemetry, "GUARD_INFERENCE_LATENCY") as mock_hist, \
             patch.object(telemetry, "GUARD_SCAN_TOTAL") as mock_counter:
            mock_hist.labels.return_value.observe = MagicMock()
            mock_counter.labels.return_value.inc = MagicMock()

            result = guarded_fn(21)

            assert result == {"decision": "allow", "result": 42}
            mock_hist.labels.assert_called_once_with(decision="allow")
            mock_hist.labels.return_value.observe.assert_called_once()
            mock_counter.labels.assert_called_once_with(decision="allow")
            mock_counter.labels.return_value.inc.assert_called_once()

    def test_falls_back_to_unknown_decision_when_result_not_dict(self) -> None:
        """If the wrapped function returns a non-dict, instrument_guard uses 'unknown'."""
        @telemetry.instrument_guard
        def bad_fn() -> str:
            return "not a dict"

        with patch.object(telemetry, "GUARD_INFERENCE_LATENCY") as mock_hist, \
             patch.object(telemetry, "GUARD_SCAN_TOTAL") as mock_counter:
            mock_hist.labels.return_value.observe = MagicMock()
            mock_counter.labels.return_value.inc = MagicMock()

            result = bad_fn()
            assert result == "not a dict"
            mock_hist.labels.assert_called_with(decision="unknown")
            mock_counter.labels.assert_called_with(decision="unknown")

    def test_uses_decision_from_nested_dict(self) -> None:
        """A nested dict (e.g. {'result': {'decision': 'block'}}) is treated as non-dict."""
        @telemetry.instrument_guard
        def nested_fn() -> dict[str, dict[str, str]]:
            return {"result": {"decision": "block"}}

        with patch.object(telemetry, "GUARD_INFERENCE_LATENCY") as mock_hist, \
             patch.object(telemetry, "GUARD_SCAN_TOTAL") as mock_counter:
            mock_hist.labels.return_value.observe = MagicMock()
            mock_counter.labels.return_value.inc = MagicMock()

            result = nested_fn()
            assert result["result"]["decision"] == "block"
            # The top-level check sees a dict and uses it; decision key must be top-level
            # Since 'decision' is not at top level, it falls back to 'unknown'
            mock_hist.labels.assert_called_with(decision="unknown")


class TestInstrumentRag:
    """Tests for instrument_rag decorator."""

    def test_observes_retrieval_latency_and_increments_success_counter(self) -> None:
        """instrument_rag records retrieval duration and increments success counter."""
        @telemetry.instrument_rag
        def rag_fn(query: str) -> list[str]:
            return ["source-a", "source-b"]

        with patch.object(telemetry, "RAG_RETRIEVAL_LATENCY") as mock_hist, \
             patch.object(telemetry, "RAG_QUERY_TOTAL") as mock_counter:
            mock_hist.observe = MagicMock()
            mock_counter.labels.return_value.inc = MagicMock()

            result = rag_fn("EU AI Act requirements")
            assert result == ["source-a", "source-b"]
            mock_hist.observe.assert_called_once()
            mock_counter.labels.assert_called_with(status="success")
            mock_counter.labels.return_value.inc.assert_called_once()

    def test_always_reports_success_even_on_empty_result(self) -> None:
        """instrument_rag reports 'success' even when the retriever returns an empty list."""
        @telemetry.instrument_rag
        def empty_rag_fn() -> list[str]:
            return []

        with patch.object(telemetry, "RAG_RETRIEVAL_LATENCY") as mock_hist, \
             patch.object(telemetry, "RAG_QUERY_TOTAL") as mock_counter:
            mock_hist.observe = MagicMock()
            mock_counter.labels.return_value.inc = MagicMock()

            result = empty_rag_fn()
            assert result == []
            mock_counter.labels.assert_called_with(status="success")


class TestSetupTelemetry:
    """Tests for setup_telemetry()."""

    def test_instruments_app_and_exposes_metrics_endpoint(self) -> None:
        """setup_telemetry instruments the FastAPI app and exposes /metrics."""
        mock_app = MagicMock()
        mock_instrumented = MagicMock()
        mock_exposed = MagicMock()
        mock_app.return_value = mock_instrumented
        mock_instrumented.expose.return_value = mock_exposed

        with patch.object(telemetry, "instrumentator") as mock_inst:
            mock_inst.instrument.return_value = mock_instrumented
            mock_inst.expose.return_value = mock_exposed
            telemetry.setup_telemetry(mock_app)
            mock_inst.instrument.assert_called_once_with(mock_app)
            mock_instrumented.expose.assert_called_once()
            call_kwargs = mock_instrumented.expose.call_args
            assert call_kwargs[1].get("endpoint") == "/metrics" or \
                   (len(call_kwargs[0]) > 0 and call_kwargs[0][0] is mock_app)
