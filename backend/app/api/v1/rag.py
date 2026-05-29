"""
RAG Intelligence API - regulatory knowledge base query endpoint.

Changed: Added query-level guard scanning, RAG audit logging, chunk-drop reporting, and grounding fields.
Why: RAG queries must be screened before retrieval and responses must expose safety/grounding metadata.
Addresses: Direct prompt injection, guard failures, poisoned retrieved chunks, and low-grounding answers.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

TODO for contributors (high difficulty):
  - Pre-load the EU AI Act, GDPR, ISO 42001, and NIST AI RMF as source documents
  - Add a POST /rag/ingest endpoint for uploading custom regulatory PDFs
  - Add streaming responses via SSE for long answers
"""

import asyncio
import hashlib
import logging
import os
import shutil
import tempfile
import time
from dataclasses import dataclass
from typing import Any, List

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Request,
    UploadFile,
    status,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.audit_log import RAGAuditLog
from app.models.rag_feedback import RAGFeedback
from app.models.rag_query import RagQuery
from app.models.user import SubscriptionTier, User
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


def load_documents_from_paths(saved_paths: list[str]):
    """Lazy wrapper around the RAG document loader."""
    from app.modules.rag.document_loader import load_documents_from_paths as loader

    return loader(saved_paths)


def create_vector_store(saved_paths: list[str]):
    """Lazy wrapper around the RAG vector-store builder."""
    from app.modules.rag.vector_store import create_vector_store as builder

    return builder(saved_paths)


def get_rag_guard() -> Any:
    """Return the module-level RAG guard singleton."""
    global _RAG_GUARD
    if _RAG_GUARD is None:
        from app.modules.guard.llm_guard import LLMGuard

        _RAG_GUARD = LLMGuard()
    return _RAG_GUARD


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


def _decision_reasoning(result: dict) -> str | None:
    """Extract human-readable reasoning from a guard result."""
    return (
        result.get("metadata", {})
        .get("decision_reasoning", {})
        .get("reasoning")
    )


def _sanitization_summary(result: dict) -> str | None:
    """Extract a compact sanitization summary from a guard result."""
    changes = (
        result.get("metadata", {})
        .get("sanitization", {})
        .get("changes")
    )
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


class RAGIngestResponse(BaseModel):
    """Response returned after a successful document ingestion."""

    files_processed: int
    chunks_created: int
    index_size_bytes: int


@router.post(
    "/ingest",
    response_model=RAGIngestResponse,
    summary="Upload & index regulatory PDFs",
    tags=["RAG Intelligence"],
)
def ingest_documents(
    files: List[UploadFile] = File(..., description="One or more PDF files to ingest"),
    current_user: User = Depends(get_current_user),
):
    """Ingest one or more regulatory PDFs and rebuild the FAISS index.

    Args:
        files: One or more PDF uploads to save, chunk, and index.
        current_user: Authenticated user requesting the ingestion.

    Returns:
        RAGIngestResponse with file, chunk, and index size counts.

    Raises:
        HTTPException: If no valid PDFs are supplied or indexing fails.
    """
    pdf_files = [
        f
        for f in files
        if f.filename
        and f.filename.lower().endswith(".pdf")
        and f.content_type in ("application/pdf", "binary/octet-stream", None)
    ]
    if not pdf_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No valid PDF files supplied. Please upload files with a .pdf extension.",
        )

    tmp_dir = tempfile.mkdtemp(prefix="aegis_ingest_")
    saved_paths: list[str] = []

    try:
        for upload in pdf_files:
            dest = os.path.join(tmp_dir, os.path.basename(upload.filename))
            with open(dest, "wb") as buf:
                shutil.copyfileobj(upload.file, buf)
            saved_paths.append(dest)

        chunks = load_documents_from_paths(saved_paths)
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Could not extract any text from the supplied PDFs. "
                    "Ensure the files are not scanned images or password-protected."
                ),
            )

        try:
            create_vector_store(saved_paths)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to build FAISS index: {exc}",
            )

        index_path = settings.FAISS_INDEX_PATH
        index_size_bytes = 0
        for fname in ("index.faiss", "index.pkl"):
            fpath = os.path.join(index_path, fname)
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
):
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
        from app.modules.rag.retrieval_chain import get_qa_chain

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
        rag_query = RagQuery(
            user_id=current_user.id,
            question=guarded_question.question,
            answer_summary=str(result.get("result", ""))[:200],
            source_count=len(sources),
        )
        db.add(rag_query)
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
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"RAG module error: {str(e)}",
        )


@router.get("/health", tags=["RAG Intelligence"])
def rag_health():
    """Check whether the RAG module has an available index."""
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


class RAGFeedbackRequest(BaseModel):
    answer_id: str
    vote: str  # "up" or "down"


@router.post("/feedback")
def rag_feedback(
    payload: RAGFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record feedback for a previously returned RAG answer."""
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
    threshold: float = 0.3,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return source chunks whose feedback ratio exceeds the threshold."""
    try:
        if current_user.subscription_tier != SubscriptionTier.SCALE:
            raise HTTPException(status_code=403, detail="Admin access required")
    except Exception:
        raise HTTPException(status_code=403, detail="Admin access required")

    counts: dict[str, dict[str, int]] = {}
    rows = db.query(RAGFeedback).all()
    for r in rows:
        total = (r.thumbs_up or 0) + (r.thumbs_down or 0)
        for chunk in r.source_chunks or []:
            if chunk not in counts:
                counts[chunk] = {"thumbs_up": 0, "thumbs_down": 0, "total": 0}
            counts[chunk]["thumbs_up"] += r.thumbs_up or 0
            counts[chunk]["thumbs_down"] += r.thumbs_down or 0
            counts[chunk]["total"] += total

    low_quality = []
    for chunk, c in counts.items():
        if c["total"] == 0:
            continue
        ratio = c["thumbs_down"] / c["total"]
        if ratio > threshold:
            low_quality.append(
                {
                    "chunk": chunk,
                    "thumbs_down": c["thumbs_down"],
                    "total": c["total"],
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
):
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
                "id": q.id,
                "question": q.question,
                "answer_summary": q.answer_summary,
                "source_count": q.source_count,
                "created_at": q.created_at,
            }
            for q in queries
        ],
    }
