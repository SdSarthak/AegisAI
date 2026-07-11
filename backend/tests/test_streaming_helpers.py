"""
Tests for backend/app/modules/rag/streaming.py helper functions.

Covers sse() formatting and _build_context_and_citations().
"""

from __future__ import annotations

import os
import pytest
from dataclasses import dataclass
from typing import Any

# Set required env vars before importing the streaming module.
# streaming.py imports app.core.config which requires these settings.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("REDIS_URL", "")

from app.modules.rag import streaming


@dataclass
class FakeDoc:
    """Minimal document stub matching the _Document protocol."""
    page_content: str
    metadata: dict[str, Any]


class TestSSE:
    """Unit tests for the sse() SSE framing helper."""

    def test_meta_event_format(self):
        """Meta event should produce correct SSE wire format."""
        data = {"answer_id": 42, "model": "gpt-4", "citations": []}
        frame = streaming.sse("meta", data)
        assert frame.startswith("event: meta\ndata: ")
        assert '"answer_id": 42' in frame
        assert '"model": "gpt-4"' in frame
        assert frame.endswith("\n\n")

    def test_token_event_format(self):
        """Token event should include delta in data."""
        frame = streaming.sse("token", {"delta": "Hello"})
        assert "event: token\n" in frame
        assert '"delta": "Hello"' in frame

    def test_done_event_format(self):
        """Done event should include finish_reason and duration_ms."""
        frame = streaming.sse("done", {"finish_reason": "stop", "duration_ms": 1234.5})
        assert "event: done\n" in frame
        assert '"finish_reason": "stop"' in frame
        assert '"duration_ms": 1234.5' in frame

    def test_error_event_format(self):
        """Error event should include code and message."""
        frame = streaming.sse("error", {"code": "retrieval_failed", "message": "no index"})
        assert "event: error\n" in frame
        assert '"code": "retrieval_failed"' in frame
        assert '"message": "no index"' in frame

    def test_unicode_escaped(self):
        """Unicode characters should be JSON-escaped in data field."""
        frame = streaming.sse("token", {"delta": "café"})
        assert "café" in frame  # JSON dumps handles unicode

    def test_special_chars_escaped(self):
        """Newlines and quotes in data should be JSON-escaped."""
        frame = streaming.sse("token", {"delta": 'line1\nline2\ttab'})
        assert r"\n" in frame or "\\n" in frame  # JSON-escaped


class TestBuildContextAndCitations:
    """Unit tests for _build_context_and_citations()."""

    def test_empty_docs_returns_empty_context(self):
        """Empty document list yields empty context and empty citations."""
        context, citations = streaming._build_context_and_citations([])
        assert context == ""
        assert citations == []

    def test_single_doc_full_context(self):
        """Single document fits entirely within MAX_CONTEXT_CHARS budget."""
        doc = FakeDoc(page_content="This is a short regulatory text about AI compliance.", metadata={"source": "eu_ai_act.pdf"})
        context, citations = streaming._build_context_and_citations([doc])
        assert "regulatory text" in context
        assert len(citations) == 1
        assert citations[0]["source"] == "eu_ai_act.pdf"
        assert "regulatory text" in citations[0]["excerpt"]

    def test_citation_excerpt_truncated_with_ellipsis(self):
        """Long content is truncated to CITATION_EXCERPT_CHARS with ellipsis."""
        long_content = "A" * 500
        doc = FakeDoc(page_content=long_content, metadata={"source": "long_doc.pdf"})
        context, citations = streaming._build_context_and_citations([doc])
        assert len(citations) == 1
        excerpt = citations[0]["excerpt"]
        assert excerpt.endswith("\u2026")  # Unicode ellipsis

    def test_context_respects_max_chars_budget(self):
        """Context string should not exceed MAX_CONTEXT_CHARS characters (budget is for content only)."""
        # Build docs that together would exceed the budget when content is summed
        # Each doc is 2000 chars; budget is 6000
        big_content = "x" * 2000
        docs = [FakeDoc(page_content=big_content, metadata={}) for _ in range(10)]
        context, citations = streaming._build_context_and_citations(docs)
        # First 3 docs: 3 * 2000 = 6000, exactly at budget; 4th would exceed
        # Context includes "---\n\n" separators: 3 docs -> 2 separators -> 14 chars
        assert len(context) <= streaming.MAX_CONTEXT_CHARS + 50  # small tolerance for separators

    def test_citations_still_populated_after_budget_exceeded(self):
        """Even when context budget is hit, citations list is fully populated."""
        big_content = "y" * 2000
        docs = [FakeDoc(page_content=big_content, metadata={"source": f"doc{i}.pdf"}) for i in range(5)]
        context, citations = streaming._build_context_and_citations(docs)
        # Context may be at budget but all citations should be present
        assert len(citations) == 5
        assert all(c["source"].startswith("doc") for c in citations)

    def test_doc_with_empty_content_skipped_in_context_and_citations(self):
        """Document with empty page_content is skipped entirely (no context, no citation)."""
        doc = FakeDoc(page_content="", metadata={"source": "empty.pdf"})
        context, citations = streaming._build_context_and_citations([doc])
        assert context == ""
        # Empty content is skipped entirely, including citation
        assert citations == []

    def test_doc_without_metadata(self):
        """Document without metadata source is handled gracefully."""
        doc = FakeDoc(page_content="Some content here.", metadata={})
        context, citations = streaming._build_context_and_citations([doc])
        assert "Some content" in context
        assert citations[0]["source"] == ""

    def test_multiple_docs_context_separators(self):
        """Multiple documents in context are separated by --- delimiter."""
        docs = [
            FakeDoc(page_content="First document text.", metadata={"source": "doc1.pdf"}),
            FakeDoc(page_content="Second document text.", metadata={"source": "doc2.pdf"}),
        ]
        context, citations = streaming._build_context_and_citations(docs)
        assert "---" in context
        assert "First document" in context
        assert "Second document" in context

    def test_null_metadata_handled(self):
        """Document with None metadata is handled."""
        doc = FakeDoc(page_content="Content here.", metadata=None)  # type: ignore
        # _build_context_and_citations uses doc.metadata.get("source", "")
        context, citations = streaming._build_context_and_citations([doc])
        assert "Content here" in context
