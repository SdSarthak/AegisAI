"""Stream RAG answers as server-sent events.

The streaming path emits metadata, token chunks, and completion events so
the frontend can render answers progressively and attach feedback to the
placeholder answer record as soon as streaming starts.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import json
import logging
import time
from typing import Any, AsyncIterator, Iterator, Protocol

import anyio
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.rag_feedback import RAGFeedback

logger = logging.getLogger("aegisai.rag.stream")

# Cap how much retrieved context we cram into the prompt. ~6k chars is a
# reasonable budget for an 8k-token context window with room for the answer.
MAX_CONTEXT_CHARS = 6000

# Excerpt length surfaced to the UI per citation — short enough to render
# in a card, long enough to be useful.
CITATION_EXCERPT_CHARS = 280

PROMPT_TEMPLATE = """You are a regulatory compliance assistant. Answer the user's question using ONLY the context below.
If the context does not contain enough information to answer, say so honestly — do not invent regulations or section numbers.
Cite the section name when you draw from it.

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""


# ---------------------------------------------------------------------------
# SSE wire format
# ---------------------------------------------------------------------------


def sse(event: str, data: dict[str, Any]) -> str:
    """Format a single Server-Sent Event frame.

    Args:
        event: SSE event name.
        data: JSON-serializable payload for the frame.

    Returns:
        A formatted SSE frame string.
    """
    return f"event: {event}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


# ---------------------------------------------------------------------------
# Type contracts (so tests can inject fakes without importing langchain)
# ---------------------------------------------------------------------------


class _Document(Protocol):
    page_content: str
    metadata: dict[str, Any]


class _Retriever(Protocol):
    def get_relevant_documents(self, query: str) -> list[_Document]: ...


class _LLM(Protocol):
    def stream(self, prompt: str, *, system_prompt: str | None = None) -> Iterator[str]: ...


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_context_and_citations(
    docs: list[_Document],
) -> tuple[str, list[dict[str, str]]]:
    """Pack retrieved chunks into a context blob and citation cards.

    Args:
        docs: Retrieved documents from the retriever.

    Returns:
        A tuple containing the assembled prompt context and citation cards.
    """
    citations: list[dict[str, str]] = []
    context_parts: list[str] = []
    used_chars = 0

    for doc in docs:
        content = (doc.page_content or "").strip()
        if not content:
            continue
        source = str(doc.metadata.get("source", "")) if doc.metadata else ""

        # Stop adding to context once we hit the budget (but keep collecting
        # citations — the user still benefits from seeing what *would* have
        # been considered).
        if used_chars + len(content) <= MAX_CONTEXT_CHARS:
            context_parts.append(content)
            used_chars += len(content)

        excerpt = content[:CITATION_EXCERPT_CHARS]
        if len(content) > CITATION_EXCERPT_CHARS:
            excerpt += "…"
        citations.append({"source": source, "excerpt": excerpt})

    return "\n\n---\n\n".join(context_parts), citations


async def _aiter_sync(sync_iter: Iterator[str]) -> AsyncIterator[str]:
    """Advance a sync iterator on a worker thread and yield on the loop.

    Args:
        sync_iter: Blocking iterator producing token deltas.

    Yields:
        String chunks produced by the synchronous iterator.
    """
    sentinel = object()

    def _next_or_sentinel() -> Any:
        try:
            return next(sync_iter)
        except StopIteration:
            return sentinel

    while True:
        chunk = await anyio.to_thread.run_sync(_next_or_sentinel)
        if chunk is sentinel:
            return
        yield chunk  # type: ignore[misc]


# ---------------------------------------------------------------------------
# The main generator
# ---------------------------------------------------------------------------


async def stream_rag_answer(
    *,
    question: str,
    retriever: _Retriever,
    llm: _LLM,
    db: Session,
    model_name: str | None = None,
) -> AsyncIterator[str]:
    """Yield SSE frames for a question as meta, token, done, or error events.

    Args:
        question: User question to answer from retrieved context.
        retriever: Retriever used to fetch supporting documents.
        llm: Streaming LLM client used to generate the response.
        db: Active database session for persisting feedback rows.
        model_name: Optional model name override for the meta event.

    Yields:
        SSE frames representing the streamed response lifecycle.
    """
    started = time.perf_counter()
    answer_buf: list[str] = []
    feedback: RAGFeedback | None = None
    sync_token_iter: Iterator[str] | None = None
    finish_reason = "stop"

    try:
        # --- 1. Retrieve --------------------------------------------------
        try:
            docs = retriever.get_relevant_documents(question)
        except Exception as exc:
            logger.exception("rag.stream.retrieval_failed")
            yield sse("error", {"code": "retrieval_failed", "message": str(exc)})
            return

        context, citations = _build_context_and_citations(docs)

        # --- 2. Persist placeholder so we have an answer_id ----------------
        feedback = RAGFeedback(
            question=question,
            answer="",
            source_chunks=[c["source"] for c in citations if c["source"]],
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        # --- 3. Emit meta -------------------------------------------------
        yield sse(
            "meta",
            {
                "answer_id": feedback.id,
                "model": model_name or settings.LLM_MODEL,
                "citations": citations,
            },
        )

        # --- 4. Stream LLM tokens ----------------------------------------
        prompt = PROMPT_TEMPLATE.format(
            context=context or "(no relevant context found)",
            question=question,
        )
        try:
            sync_token_iter = llm.stream(prompt)
            async for delta in _aiter_sync(sync_token_iter):
                if not delta:
                    continue
                answer_buf.append(delta)
                yield sse("token", {"delta": delta})
        except Exception as exc:
            logger.exception("rag.stream.llm_failed")
            yield sse("error", {"code": "llm_failed", "message": str(exc)})
            finish_reason = "error"
            return

        # --- 5. Emit done -------------------------------------------------
        duration_ms = round((time.perf_counter() - started) * 1000, 2)
        yield sse(
            "done",
            {"finish_reason": finish_reason, "duration_ms": duration_ms},
        )

    except GeneratorExit:
        # Client disconnected. Don't try to yield anything else (the
        # downstream send is gone) — just record the partial state and
        # propagate the close.
        finish_reason = "cancelled"
        logger.info("rag.stream.client_disconnected")
        raise
    finally:
        # Close the upstream LLM connection so we don't keep generating /
        # billing tokens after the client is gone. Best-effort: the openai
        # stream's close() releases the underlying HTTP response.
        if sync_token_iter is not None:
            try:
                sync_token_iter.close()
            except Exception:
                logger.debug("rag.stream.iter_close_failed", exc_info=True)

        # Persist whatever we managed to generate. Even on cancel the user
        # may want to thumbs-up/down a partial answer.
        if feedback is not None and answer_buf:
            try:
                feedback.answer = "".join(answer_buf)
                db.add(feedback)
                db.commit()
            except Exception:
                logger.exception("rag.stream.feedback_persist_failed")
                db.rollback()
