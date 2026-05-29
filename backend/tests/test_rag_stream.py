"""
Tests for POST /api/v1/rag/query/stream — SSE-streamed RAG answers.

Same mock-heavy pattern as test_rag_ingest.py: every heavy dependency
(vector store, embeddings, LLM client) is patched so the tests run
without an OpenAI key, a running DB, or a real FAISS index.
"""

from __future__ import annotations
from app.core.config import settings
import json
from dataclasses import dataclass, field
from typing import Iterator
from unittest.mock import MagicMock, patch

import pytest

from app.modules.rag import streaming


# ---------------------------------------------------------------------------
# Fakes
# ---------------------------------------------------------------------------


@dataclass
class _FakeDoc:
    page_content: str
    metadata: dict = field(default_factory=dict)


class _FakeRetriever:
    def __init__(self, docs):
        self._docs = docs
        self.calls = 0

    def get_relevant_documents(self, query):  # noqa: D401 — protocol method
        self.calls += 1
        return list(self._docs)


class _FakeLLM:
    """Yields deltas synchronously, just like LLMClient.stream."""

    def __init__(self, deltas, raise_after=None):
        self._deltas = list(deltas)
        self._raise_after = raise_after
        self.closed = False

    def stream(self, prompt, system_prompt=None):  # noqa: D401
        def _iter():
            try:
                for i, d in enumerate(self._deltas):
                    if self._raise_after is not None and i >= self._raise_after:
                        raise RuntimeError("simulated llm failure")
                    yield d
            finally:
                self.closed = True

        return _iter()


def _mock_current_user():
    u = MagicMock()
    u.id = 1
    u.email = "test@example.com"
    return u


def _parse_sse(payload: bytes | str) -> list[dict]:
    """Parse an SSE byte stream into [{event, data}, ...]."""
    text = payload.decode() if isinstance(payload, bytes) else payload
    events = []
    for block in text.split("\n\n"):
        block = block.strip()
        if not block:
            continue
        event, data = None, None
        for line in block.splitlines():
            if line.startswith("event: "):
                event = line[len("event: "):].strip()
            elif line.startswith("data: "):
                data = line[len("data: "):]
        if event is not None and data is not None:
            events.append({"event": event, "data": json.loads(data)})
    return events


# ---------------------------------------------------------------------------
# Unit tests for the generator (no FastAPI involved)
# ---------------------------------------------------------------------------


class TestStreamRagAnswer:
    @pytest.mark.asyncio
    async def test_emits_meta_token_done_in_order(self, db_session):
        retriever = _FakeRetriever(
            [
                _FakeDoc("Article 6: high-risk systems include CV screening tools.",
                         {"source": "eu_ai_act.pdf"}),
                _FakeDoc("Recital 28 explains the transparency rationale.",
                         {"source": "eu_ai_act.pdf"}),
            ]
        )
        llm = _FakeLLM(["The ", "EU AI Act ", "classifies ", "CV ", "screening ", "as ", "high-risk."])

        events = []
        async for frame in streaming.stream_rag_answer(
            question="Is my CV screener high-risk?",
            retriever=retriever,
            llm=llm,
            db=db_session,
            model_name=settings.LLM_MODEL,
        ):
            events.extend(_parse_sse(frame))

        kinds = [e["event"] for e in events]
        # Exactly one meta, one or more token, exactly one done — in that order.
        assert kinds[0] == "meta"
        assert kinds[-1] == "done"
        assert kinds.count("meta") == 1
        assert kinds.count("done") == 1
        assert all(k == "token" for k in kinds[1:-1])

        meta = events[0]["data"]
        assert meta["model"] == "llama3.2"
        assert isinstance(meta["answer_id"], str)
        assert len(meta["answer_id"]) >= 32  # uuid hex with dashes
        assert len(meta["citations"]) == 2
        assert meta["citations"][0]["source"] == "eu_ai_act.pdf"

        # Full answer is the concatenation of token deltas.
        tokens = [e["data"]["delta"] for e in events if e["event"] == "token"]
        assert "".join(tokens) == "The EU AI Act classifies CV screening as high-risk."

        done = events[-1]["data"]
        assert done["finish_reason"] == "stop"
        assert done["duration_ms"] >= 0

    @pytest.mark.asyncio
    async def test_retrieval_failure_emits_error_and_stops(self, db_session):
        class _Broken:
            def get_relevant_documents(self, q):
                raise RuntimeError("faiss index corrupt")

        events = []
        async for frame in streaming.stream_rag_answer(
            question="anything",
            retriever=_Broken(),
            llm=_FakeLLM(["unused"]),
            db=db_session,
            model_name=settings.LLM_MODEL
        ):
            events.extend(_parse_sse(frame))

        assert len(events) == 1
        assert events[0]["event"] == "error"
        assert events[0]["data"]["code"] == "retrieval_failed"
        assert "faiss" in events[0]["data"]["message"].lower()

    @pytest.mark.asyncio
    async def test_llm_failure_emits_error_after_meta(self, db_session):
        retriever = _FakeRetriever([_FakeDoc("ctx", {"source": "x"})])
        # raise_after=1 means: yield index 0, then on index 1 raise.
        # We need at least 2 deltas in the list for that branch to execute.
        llm = _FakeLLM(["partial ", "unreachable"], raise_after=1)

        events = []
        async for frame in streaming.stream_rag_answer(
            question="q",
            retriever=retriever,
            llm=llm,
            db=db_session,
            model_name=settings.LLM_MODEL
        ):
            events.extend(_parse_sse(frame))

        kinds = [e["event"] for e in events]
        assert kinds[0] == "meta"
        # one token already arrived before the failure
        assert "token" in kinds
        assert kinds[-1] == "error"
        assert events[-1]["data"]["code"] == "llm_failed"
        # llm.stream's finally block must have run, releasing the connection
        assert llm.closed is True

    @pytest.mark.asyncio
    async def test_persists_answer_id_and_final_text(self, db_session):
        from app.models.rag_feedback import RAGFeedback

        retriever = _FakeRetriever([_FakeDoc("c", {"source": "doc.pdf"})])
        llm = _FakeLLM(["Hello ", "world."])

        events = []
        async for frame in streaming.stream_rag_answer(
            question="hi",
            retriever=retriever,
            llm=llm,
            db=db_session,
            model_name=settings.LLM_MODEL
        ):
            events.extend(_parse_sse(frame))

        answer_id = events[0]["data"]["answer_id"]
        row = db_session.query(RAGFeedback).filter(RAGFeedback.id == answer_id).first()
        assert row is not None
        assert row.question == "hi"
        assert row.answer == "Hello world."
        assert row.source_chunks == ["doc.pdf"]

    @pytest.mark.asyncio
    async def test_client_disconnect_closes_llm_iter(self, db_session):
        retriever = _FakeRetriever([_FakeDoc("c", {"source": "x"})])
        llm = _FakeLLM(["one ", "two ", "three ", "four ", "five"])

        gen = streaming.stream_rag_answer(
            question="q", retriever=retriever, llm=llm, db=db_session, model_name=settings.LLM_MODEL
        )

        # Consume the meta event and one token, then close as if the
        # downstream HTTP connection had been dropped.
        seen_kinds = []
        seen_tokens = 0
        async for frame in gen:
            for ev in _parse_sse(frame):
                seen_kinds.append(ev["event"])
                if ev["event"] == "token":
                    seen_tokens += 1
                    if seen_tokens == 1:
                        await gen.aclose()
                        break
            if seen_tokens == 1:
                break

        assert "meta" in seen_kinds
        assert llm.closed is True


# ---------------------------------------------------------------------------
# Helper-function tests
# ---------------------------------------------------------------------------


class TestSseHelpers:
    def test_sse_frame_format(self):
        frame = streaming.sse("token", {"delta": "hi"})
        assert frame.startswith("event: token\n")
        assert "data: " in frame
        assert frame.endswith("\n\n")
        # roundtrip
        events = _parse_sse(frame)
        assert events == [{"event": "token", "data": {"delta": "hi"}}]

    def test_context_truncation_keeps_citations(self):
        big = "X" * (streaming.MAX_CONTEXT_CHARS + 5000)
        docs = [
            _FakeDoc(big, {"source": "a.pdf"}),
            _FakeDoc("small", {"source": "b.pdf"}),
        ]
        context, citations = streaming._build_context_and_citations(docs)
        # First doc fits; second is skipped from context because over budget,
        # but still surfaces as a citation card.
        assert len(context) <= streaming.MAX_CONTEXT_CHARS + 100  # small slack
        assert {c["source"] for c in citations} == {"a.pdf", "b.pdf"}

    def test_excerpt_truncation_adds_ellipsis(self):
        long_content = "a" * (streaming.CITATION_EXCERPT_CHARS + 50)
        docs = [_FakeDoc(long_content, {"source": "x.pdf"})]
        _, citations = streaming._build_context_and_citations(docs)
        assert citations[0]["excerpt"].endswith("…")


# ---------------------------------------------------------------------------
# Integration test through the FastAPI endpoint
# ---------------------------------------------------------------------------


class TestQueryStreamEndpoint:
    """End-to-end via TestClient — proves headers + plumbing are correct."""

    def test_streams_events_in_order(self, client):
        from app.core.security import get_current_user
        from app.main import app

        fake_retriever = _FakeRetriever(
            [_FakeDoc("article text", {"source": "law.pdf"})]
        )
        fake_llm = _FakeLLM(["Yes", ", ", "it is."])

        fake_vs = MagicMock()
        fake_vs.as_retriever.return_value = fake_retriever

        app.dependency_overrides[get_current_user] = _mock_current_user

        try:
            with patch("app.api.v1.rag.load_vector_store", return_value=fake_vs), \
                 patch("app.api.v1.rag.LLMClient", return_value=fake_llm):

                with client.stream(
                    "POST",
                    "/api/v1/rag/query/stream",
                    json={"question": "is X high-risk?"},
                ) as resp:
                    assert resp.status_code == 200
                    assert resp.headers["content-type"].startswith("text/event-stream")
                    assert resp.headers["cache-control"] == "no-cache"
                    assert resp.headers["x-accel-buffering"] == "no"

                    body = b"".join(resp.iter_bytes())
        finally:
            app.dependency_overrides.pop(get_current_user, None)

        events = _parse_sse(body)
        kinds = [e["event"] for e in events]
        assert kinds[0] == "meta"
        assert kinds[-1] == "done"
        assert events[0]["data"]["citations"][0]["source"] == "law.pdf"
        tokens = [e["data"]["delta"] for e in events if e["event"] == "token"]
        assert "".join(tokens) == "Yes, it is."

    def test_returns_503_when_index_missing(self, client):
        from app.core.security import get_current_user
        from app.main import app

        app.dependency_overrides[get_current_user] = _mock_current_user
        try:
            with patch(
                "app.api.v1.rag.load_vector_store",
                side_effect=FileNotFoundError("FAISS index missing"),
            ):
                resp = client.post(
                    "/api/v1/rag/query/stream",
                    json={"question": "anything"},
                )
            assert resp.status_code == 503
            assert "missing" in resp.json()["detail"].lower()
        finally:
            app.dependency_overrides.pop(get_current_user, None)