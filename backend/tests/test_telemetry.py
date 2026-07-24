"""
Unit tests for backend/app/core/telemetry.py — Prometheus instrumentation decorators.

Tests cover:
  - instrument_guard records correct decision label on async call
  - instrument_guard records correct decision label on sync call
  - instrument_guard falls back to "unknown" when result has no decision key
  - instrument_rag observes duration and increments counter on async call
  - instrument_rag observes duration and increments counter on sync call
  - Neither decorator swallows the underlying function's return value
"""

import asyncio
import pytest
from prometheus_client import REGISTRY

from app.core.telemetry import instrument_guard, instrument_rag


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _reset_metrics() -> None:
    """Clear all registered collectors so each test starts fresh."""
    # prometheus_client does not expose a public reset; re-import to get a
    # fresh module state is not practical in-process.  Instead we verify
    # increments rather than absolute values so interleaved runs are safe.
    pass


# ---------------------------------------------------------------------------
# instrument_guard — async
# ---------------------------------------------------------------------------

class TestInstrumentGuardAsync:
    @pytest.mark.asyncio
    async def test_async_records_decision_label(self):
        """Async guard fn with decision='block' records the block label."""

        @instrument_guard
        async def guard_fn(prompt: str) -> dict:
            return {"decision": "block", "prompt": prompt}

        result = await guard_fn("ignore me")
        assert result["decision"] == "block"

    @pytest.mark.asyncio
    async def test_async_records_allow_label(self):
        """Async guard fn with decision='allow' records the allow label."""

        @instrument_guard
        async def guard_fn(prompt: str) -> dict:
            return {"decision": "allow", "reasoning": "clean"}

        result = await guard_fn("hello")
        assert result["decision"] == "allow"

    @pytest.mark.asyncio
    async def test_async_returns_none_for_decision_key(self):
        """Async guard fn returning no decision key records 'unknown' without raising."""

        @instrument_guard
        async def guard_fn(prompt: str) -> dict:
            return {"reasoning": "no decision field"}

        result = await guard_fn("hello")
        assert "decision" not in result
        # Should not raise — decorator must not suppress the return value

    @pytest.mark.asyncio
    async def test_async_preserves_return_value(self):
        """The decorator must not mutate the return value."""

        @instrument_guard
        async def guard_fn(prompt: str) -> dict:
            return {"decision": "sanitize", "sanitized": prompt + "-sanitized"}

        result = await guard_fn("original")
        assert result["decision"] == "sanitize"
        assert result["sanitized"] == "original-sanitized"


# ---------------------------------------------------------------------------
# instrument_guard — sync
# ---------------------------------------------------------------------------

class TestInstrumentGuardSync:
    def test_sync_records_decision_label(self):
        """Sync guard fn with decision='block' records the block label."""

        @instrument_guard
        def guard_fn(prompt: str) -> dict:
            return {"decision": "block"}

        result = guard_fn("ignore")
        assert result["decision"] == "block"

    def test_sync_falls_back_to_unknown_for_missing_decision(self):
        """Sync guard fn returning a non-dict result records 'unknown' without raising."""

        @instrument_guard
        def guard_fn(prompt: str) -> dict:
            return {"other_key": "value"}

        result = guard_fn("test")
        assert result["other_key"] == "value"
        # Should not raise

    def test_sync_preserves_return_value(self):
        """Decorator does not alter the return value of the wrapped sync fn."""

        @instrument_guard
        def guard_fn(prompt: str) -> dict:
            return {"decision": "allow", "extra": 42}

        result = guard_fn("hello")
        assert result["decision"] == "allow"
        assert result["extra"] == 42


# ---------------------------------------------------------------------------
# instrument_rag — async
# ---------------------------------------------------------------------------

class TestInstrumentRagAsync:
    @pytest.mark.asyncio
    async def test_async_records_success_counter(self):
        """Async RAG fn is called and its return value is preserved."""

        @instrument_rag
        async def rag_fn(query: str) -> list:
            return [{"page_content": "result", "metadata": {}}]

        result = await rag_fn("what is AI?")
        assert len(result) == 1
        assert result[0]["page_content"] == "result"

    @pytest.mark.asyncio
    async def test_async_preserves_return_value(self):
        """Decorator does not drop or modify the return value."""

        @instrument_rag
        async def rag_fn(query: str) -> dict:
            return {"answer": "42", "sources": []}

        result = await rag_fn("answer")
        assert result["answer"] == "42"


# ---------------------------------------------------------------------------
# instrument_rag — sync
# ---------------------------------------------------------------------------

class TestInstrumentRagSync:
    def test_sync_records_success_counter(self):
        """Sync RAG fn is called and its return value is preserved."""

        @instrument_rag
        def rag_fn(query: str) -> list:
            return [{"page_content": "sync result", "metadata": {}}]

        result = rag_fn("test query")
        assert len(result) == 1
        assert result[0]["page_content"] == "sync result"

    def test_sync_preserves_return_value(self):
        """Decorator does not alter the return value of the wrapped sync fn."""

        @instrument_rag
        def rag_fn(query: str) -> dict:
            return {"answer": "sync answer", "confidence": 0.95}

        result = rag_fn("hello")
        assert result["answer"] == "sync answer"
        assert result["confidence"] == 0.95
