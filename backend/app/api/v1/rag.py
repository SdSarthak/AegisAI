"""
RAG Intelligence API - regulatory knowledge base query endpoint.

Changed: Merged guarded RAG query handling with upstream streaming support.
Why: RAG queries need prompt-injection protection, audit logging, grounding
metadata, and the new SSE endpoint must remain available after merging main.
Addresses: Direct prompt injection, poisoned retrieved chunks, low-grounding
answers, and route loss during upstream conflict resolution.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import asyncio
import hashlib
import logging
import mimetypes
import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from typing import Any, List, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.audit_log import RAGAuditLog
from app.models.rag_feedback import RAGFeedback
from app.models.rag_query import RagQuery
from app.models.user import SubscriptionTier, User
from app.modules.llm.llm_client import LLMClient
from app.modules.rag.document_loader import load_documents_from_paths
from app.modules.rag.streaming import stream_rag_answer
from app.modules.rag.vector_store import create_vector_store, load_vector_store
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse

router = APIRouter()
logger = logging.getLogger(__name__)
_RAG_GUARD: Any | None = None


@dataclass(frozen=True)
class GuardedRAGQuestion:
    """Question text approved for retrieval plus guard metadata."""

    question: str
    original_question: str
    guard_triggered: bool
    guard_decision: str
    reasoning: str | None = None
    changes_summary: str | None = None


class RAGIngestResponse(BaseModel):
    """Response returned after a successful document ingestion."""

    files_processed: int
    chunks_created: int
    index_size_bytes: int


class RAGFeedbackRequest(BaseModel):
    """Feedback payload for a previously returned RAG answer."""

    answer_id: str
    vote: Literal["up", "down"]


def get_rag_guard() -> Any:
    """Return the module-level RAG guard singleton."""
    global _RAG_GUARD
    if _RAG_GUARD is None:
        from app.modules.guard.llm_guard import LLMGuard

        _RAG_GUARD = LLMGuard()
    return _RAG_GUARD


def get_qa_chain() -> Any:
    """Return the configured RAG QA chain."""
    from app.modules.rag.retrieval_chain import get_qa_chain as chain_factory

    return chain_factory()


def _hash_question(question: str) -> str:
    """Return a SHA-256 digest for a question without exposing raw text."""
    return hashlib.sha256(question.encode("utf-8")).hexdigest()


def _client_ip(request: Request) -> str | None:
    """Extract the client IP address when available."""
    return request.client.host if request.client else None


def _log_rag_audit(
    db: Session,
    *,
    user_id: int | None,
    question: str,
    event_type: str,
    decision: str,
    request: Request,
    reasoning: str | None = None,
    changes_summary: str | None = None,
    chunks_total: int | None = None,
    chunks_dropped: int | None = None,
    grounding_score: float | None = None,
) -> None:
    """Persist a RAG audit record using only a question hash."""
    try:
        db.add(
            RAGAuditLog(
                user_id=user_id,
                event_type=event_type,
                question_hash=_hash_question(question),
                decision=decision,
                reasoning=reasoning,
                changes_summary=changes_summary,
                chunks_total=chunks_total,
                chunks_dropped=chunks_dropped,
                grounding_score=grounding_score,
                ip_address=_client_ip(request),
            )
        )
        db.commit()
    except Exception:
        db.rollback()
        logger.exception("Failed to write RAG audit log")


def _decision_reasoning(result: dict[str, Any]) -> str | None:
    """Extract human-readable reasoning from a guard result."""
    return result.get("metadata", {}).get("decision_reasoning", {}).get("reasoning")


def _sanitization_summary(result: dict[str, Any]) -> str | None:
    """Extract a compact sanitization summary from a guard result."""
    changes = result.get("metadata", {}).get("sanitization", {}).get("changes")
    if changes is None:
        return None
    return str(changes)


async def guard_rag_question(
    payload: RAGQueryRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
) -> GuardedRAGQuestion:
    """Scan the incoming RAG question before retrieval and fail closed."""
    del request, current_user
    loop = asyncio.get_event_loop()

    try:
        guard = get_rag_guard()
        result = await loop.run_in_executor(None, guard.guard, payload.question)
    except Exception as exc:
        return GuardedRAGQuestion(
            question=payload.question,
            original_question=payload.question,
            guard_triggered=True,
            guard_decision="ERROR",
            reasoning=str(exc),
        )

    decision = str(result.get("decision", "allow")).upper()
    reasoning = _decision_reasoning(result)

    if decision == "BLOCK":
        return GuardedRAGQuestion(
            question=payload.question,
            original_question=payload.question,
            guard_triggered=True,
            guard_decision="BLOCK",
            reasoning=reasoning,
        )

    if decision == "SANITIZE":
        sanitized_question = str(result.get("sanitized_prompt", payload.question))
        return GuardedRAGQuestion(
            question=sanitized_question,
            original_question=payload.question,
            guard_triggered=True,
            guard_decision="SANITIZE",
            reasoning=reasoning,
            changes_summary=_sanitization_summary(result),
        )

    return GuardedRAGQuestion(
        question=payload.question,
        original_question=payload.question,
        guard_triggered=False,
        guard_decision="ALLOW",
        reasoning=reasoning,
    )


@router.post(
    "/ingest",
    response_model=RAGIngestResponse,
    summary="Upload & index regulatory PDFs",
    tags=["RAG Intelligence"],
)
def ingest_documents(
    files: List[UploadFile] = File(..., description="One or more PDF files to ingest"),
    current_user: User = Depends(get_current_user),
) -> RAGIngestResponse:
    """Upload regulatory PDFs, chunk them, and rebuild the persisted FAISS index."""
    del current_user
    if len(files) > settings.RAG_MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Too many files. Maximum allowed is {settings.RAG_MAX_FILES_PER_REQUEST}.",
        )

    pdf_files = [
        upload
        for upload in files
        if upload.filename
        and upload.filename.lower().endswith(".pdf")
        and mimetypes.guess_type(upload.filename)[0]
        in ("application/pdf", "binary/octet-stream", None)
    ]
    if not pdf_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid PDF files supplied. Please upload files with a .pdf extension.",
        )

    total_size = 0
    for upload in pdf_files:
        upload.file.seek(0, 2)
        file_size = upload.file.tell()
        upload.file.seek(0)

        if file_size > settings.RAG_MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"File {upload.filename} exceeds the maximum size of "
                    f"{settings.RAG_MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB."
                ),
            )
        total_size += file_size

    if total_size > settings.RAG_TOTAL_BUDGET_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                "Total upload size exceeds the maximum budget of "
                f"{settings.RAG_TOTAL_BUDGET_BYTES // (1024 * 1024)}MB."
            ),
        )

    tmp_dir = tempfile.mkdtemp(prefix="aegis_ingest_")
    saved_paths: list[str] = []

    try:
        for upload in pdf_files:
            dest = os.path.join(tmp_dir, os.path.basename(upload.filename))
            with open(dest, "wb") as buf:
                shutil.copyfileobj(upload.file, buf)
            saved_paths.append(dest)

        raw_chunks = load_documents_from_paths(saved_paths)
        chunks = [
            chunk
            for chunk in raw_chunks
            if chunk.page_content and chunk.page_content.strip()
        ]

        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Could not extract any valid text from the supplied PDFs. "
                    "Ensure the files are not scanned images or password-protected."
                ),
            )

        try:
            create_vector_store(chunks)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to build FAISS index: {exc}",
            )

        index_size_bytes = 0
        for fname in ("index.faiss", "index.pkl"):
            fpath = os.path.join(settings.FAISS_INDEX_PATH, fname)
            if os.path.exists(fpath):
                index_size_bytes += os.path.getsize(fpath)

        return RAGIngestResponse(
            files_processed=len(saved_paths),
            chunks_created=len(chunks),
            index_size_bytes=index_size_bytes,
        )

    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/query", response_model=RAGQueryResponse)
def query_knowledge_base(
    http_request: Request,
    current_user: User = Depends(get_current_user),
    guarded_question: GuardedRAGQuestion = Depends(guard_rag_question),
    db: Session = Depends(get_db),
) -> RAGQueryResponse:
    """Ask a regulatory question and get an answer grounded in source documents."""
    try:
        if guarded_question.guard_decision == "ERROR":
            _log_rag_audit(
                db,
                user_id=getattr(current_user, "id", None),
                question=guarded_question.original_question,
                event_type="RAG_GUARD_ERROR",
                decision="ERROR",
                request=http_request,
                reasoning=guarded_question.reasoning,
            )
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail={
                    "error": "guard_unavailable",
                    "safe_message": "The query safety scanner is unavailable.",
                },
            )

        if guarded_question.guard_decision == "BLOCK":
            _log_rag_audit(
                db,
                user_id=getattr(current_user, "id", None),
                question=guarded_question.original_question,
                event_type="RAG_QUERY_BLOCKED",
                decision="BLOCK",
                request=http_request,
                reasoning=guarded_question.reasoning,
            )
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={
                    "error": "query_blocked",
                    "reason": guarded_question.reasoning,
                    "safe_message": (
                        "Your query contains patterns that cannot be processed."
                    ),
                },
            )

        if guarded_question.guard_decision == "SANITIZE":
            _log_rag_audit(
                db,
                user_id=getattr(current_user, "id", None),
                question=guarded_question.original_question,
                event_type="RAG_QUERY_SANITIZED",
                decision="SANITIZE",
                request=http_request,
                reasoning=guarded_question.reasoning,
                changes_summary=guarded_question.changes_summary,
            )

        from app.core.database import Base

        qa_chain = get_qa_chain()
        t_start = time.monotonic()
        result = qa_chain({"query": guarded_question.question})
        latency_ms = (time.monotonic() - t_start) * 1000

        source_docs = result.get("source_documents", [])
        sources = [dict(getattr(doc, "metadata", {}) or {}) for doc in source_docs]
        source_labels = [str(source.get("source", "")) for source in sources]
        answer = str(result.get("result", ""))
        chunks_total = int(result.get("chunks_total", len(source_docs)))
        chunks_dropped = int(result.get("chunks_dropped", 0))
        grounding_score = float(result.get("grounding_score", 0.0))
        grounding_confidence = str(result.get("grounding_confidence", "LOW")).upper()
        warning = result.get("warning")

        if chunks_dropped:
            _log_rag_audit(
                db,
                user_id=getattr(current_user, "id", None),
                question=guarded_question.original_question,
                event_type="RAG_CHUNK_DROPPED",
                decision=guarded_question.guard_decision,
                request=http_request,
                chunks_total=chunks_total,
                chunks_dropped=chunks_dropped,
            )

        if grounding_confidence == "LOW":
            _log_rag_audit(
                db,
                user_id=getattr(current_user, "id", None),
                question=guarded_question.original_question,
                event_type="RAG_LOW_GROUNDING",
                decision=guarded_question.guard_decision,
                request=http_request,
                chunks_total=chunks_total,
                chunks_dropped=chunks_dropped,
                grounding_score=grounding_score,
                reasoning=warning,
            )

        try:
            Base.metadata.create_all(bind=db.get_bind())
        except Exception:
            pass

        feedback = RAGFeedback(
            question=guarded_question.question,
            answer=answer,
            source_chunks=source_labels,
        )
        db.add(feedback)
        db.add(
            RagQuery(
                user_id=current_user.id,
                question=guarded_question.question,
                answer_summary=answer[:200],
                source_count=len(sources),
            )
        )
        db.commit()
        db.refresh(feedback)

        try:
            from app.modules.rag.ml_flow import log_query

            log_query(
                question=guarded_question.question,
                answer=answer,
                sources=source_labels,
                latency_ms=latency_ms,
            )
        except Exception:
            pass

        return RAGQueryResponse(
            answer=answer,
            sources=sources,
            answer_id=feedback.id,
            grounding_score=grounding_score,
            grounding_confidence=grounding_confidence,
            guard_triggered=guarded_question.guard_triggered,
            guard_decision=guarded_question.guard_decision,
            chunks_total=chunks_total,
            chunks_dropped=chunks_dropped,
            warning=warning,
            groundedness_score=grounding_score,
            low_confidence=grounding_confidence == "LOW",
            confidence_tier=grounding_confidence.lower(),
            flagged_reason=warning,
        )
    except HTTPException:
        raise
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"RAG module error: {str(exc)}",
        )


@router.post(
    "/query/stream",
    summary="Stream a regulatory answer token-by-token (SSE)",
    tags=["RAG Intelligence"],
    responses={
        200: {
            "description": (
                "Server-Sent Events stream. Emits one meta event with citations "
                "and answer_id, then token events, then a terminal done event."
            ),
            "content": {"text/event-stream": {}},
        }
    },
)
async def query_knowledge_base_stream(
    request: Request,
    payload: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Stream a regulatory answer as Server-Sent Events."""
    del request, current_user
    try:
        vector_store = load_vector_store()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    retriever = vector_store.as_retriever(search_kwargs={"k": 5})
    llm_client = LLMClient()

    generator = stream_rag_answer(
        question=payload.question,
        retriever=retriever,
        llm=llm_client,
        db=db,
        model_name=settings.LLM_MODEL,
    )

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/health", tags=["RAG Intelligence"])
def rag_health() -> dict[str, Any]:
    """Check if the RAG module is available."""
    from app.modules.rag.vector_store import check_index_exists

    index_loaded = check_index_exists()

    if not index_loaded:
        return {
            "module": "rag_intelligence",
            "status": "unavailable",
            "index_loaded": False,
            "message": (
                "FAISS index not found. RAG module requires document ingestion before use."
            ),
        }

    return {
        "module": "rag_intelligence",
        "status": "available",
        "index_loaded": True,
    }


@router.post("/feedback")
def rag_feedback(
    payload: RAGFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Record a thumbs-up or thumbs-down for a previously returned answer."""
    del current_user
    fb = db.query(RAGFeedback).filter(RAGFeedback.id == payload.answer_id).first()
    if not fb:
        raise HTTPException(status_code=404, detail="Answer not found")
    if payload.vote == "up":
        fb.thumbs_up = (fb.thumbs_up or 0) + 1
    else:
        fb.thumbs_down = (fb.thumbs_down or 0) + 1
    db.add(fb)
    db.commit()
    db.refresh(fb)
    return {"status": "ok", "answer_id": fb.id}


@router.get("/low-quality-chunks")
def get_low_quality_chunks(
    threshold: float = Query(0.3, ge=0, le=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Aggregate feedback by source chunk and return low-quality candidates."""
    try:
        if current_user.subscription_tier != SubscriptionTier.SCALE:
            raise HTTPException(status_code=403, detail="Admin access required")
    except Exception:
        raise HTTPException(status_code=403, detail="Admin access required")

    counts: dict[str, dict[str, int]] = {}
    rows = db.query(RAGFeedback).all()
    for row in rows:
        total = (row.thumbs_up or 0) + (row.thumbs_down or 0)
        for chunk in row.source_chunks or []:
            counts.setdefault(chunk, {"thumbs_up": 0, "thumbs_down": 0, "total": 0})
            counts[chunk]["thumbs_up"] += row.thumbs_up or 0
            counts[chunk]["thumbs_down"] += row.thumbs_down or 0
            counts[chunk]["total"] += total

    low_quality = []
    for chunk, count in counts.items():
        if count["total"] == 0:
            continue
        ratio = count["thumbs_down"] / count["total"]
        if ratio > threshold:
            low_quality.append(
                {
                    "chunk": chunk,
                    "thumbs_down": count["thumbs_down"],
                    "total": count["total"],
                    "ratio": ratio,
                }
            )

    return {"threshold": threshold, "low_quality_chunks": low_quality}


@router.get("/history")
def get_rag_history(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, Any]:
    """Return the current user's paginated RAG query history."""
    offset = (page - 1) * page_size
    queries = (
        db.query(RagQuery)
        .filter(RagQuery.user_id == current_user.id)
        .order_by(RagQuery.created_at.desc())
        .offset(offset)
        .limit(page_size)
        .all()
    )
    return {
        "page": page,
        "page_size": page_size,
        "results": [
            {
                "id": query.id,
                "question": query.question,
                "answer_summary": query.answer_summary,
                "source_count": query.source_count,
                "created_at": query.created_at,
            }
            for query in queries
        ],
    }
