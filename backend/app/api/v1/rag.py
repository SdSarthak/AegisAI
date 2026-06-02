"""
RAG Intelligence API - regulatory knowledge base query endpoint.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
   
 
TODO for contributors (high difficulty):
  - Pre-load the EU AI Act, GDPR, ISO 42001, and NIST AI RMF as source documents
  - Add a POST /rag/ingest endpoint for uploading custom regulatory PDFs
  - Add streaming responses via SSE for long answers
"""

import os
import shutil
import tempfile
import time
from typing import List, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.rag_feedback import RAGFeedback
from app.models.rag_query import RagQuery
from app.core.metrics import RAG_QUERIES_TOTAL
from app.models.user import SubscriptionTier, User
from app.schemas.rag import RAGQueryRequest, RAGQueryResponse
router = APIRouter()


def load_documents_from_paths(saved_paths: list[str]):
    """Lazy wrapper around the RAG document loader."""
    from app.modules.rag.document_loader import load_documents_from_paths as loader

    return loader(saved_paths)


def create_vector_store(saved_paths: list[str]):
    """Lazy wrapper around the RAG vector-store builder."""
    from app.modules.rag.vector_store import create_vector_store as builder

    return builder(saved_paths)


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
    if len(files) > settings.RAG_MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Too many files. Maximum allowed is {settings.RAG_MAX_FILES_PER_REQUEST}.",
        )

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

    total_size = 0
    for upload in pdf_files:
        upload.file.seek(0, 2)
        file_size = upload.file.tell()
        upload.file.seek(0)

        if file_size > settings.RAG_MAX_FILE_SIZE_BYTES:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=f"File {upload.filename} exceeds the maximum size of {settings.RAG_MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB.",
            )
        total_size += file_size

    if total_size > settings.RAG_TOTAL_BUDGET_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Total upload size exceeds the maximum budget of {settings.RAG_TOTAL_BUDGET_BYTES // (1024 * 1024)}MB.",
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
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ask a regulatory question and get an answer grounded in source documents."""
    try:
        from app.core.database import Base
        from app.modules.rag.retrieval_chain import get_qa_chain

        qa_chain = get_qa_chain()

        t_start = time.monotonic()
        result = qa_chain({"query": request.question})
        RAG_QUERIES_TOTAL.inc()
        latency_ms = (time.monotonic() - t_start) * 1000

        source_docs = result.get("source_documents", [])
        sources = [str(doc.metadata.get("source", "")) for doc in source_docs]
        answer = str(result.get("result", ""))

        try:
            Base.metadata.create_all(bind=db.get_bind())
        except Exception:
            pass

        feedback = RAGFeedback(
            question=request.question,
            answer=answer,
            source_chunks=sources,
        )
        db.add(feedback)
        rag_query = RagQuery(
            user_id=current_user.id,
            question=request.question,
            answer_summary=str(result.get("result", ""))[:200],
            source_count=len(sources),
        )
        db.add(rag_query)
        db.commit()
        db.refresh(feedback)

        try:
            from app.modules.rag.ml_flow import log_query

            log_query(
                question=request.question,
                answer=answer,
                sources=sources,
                latency_ms=latency_ms,
            )
        except Exception:
            pass

        return RAGQueryResponse(
            answer=answer,
            sources=sources,
            answer_id=feedback.id,
            groundedness_score=result.get("groundedness_score", 0.0),
            low_confidence=result.get("low_confidence", False),
            confidence_tier=result.get("confidence_tier", "unknown"),
            per_verifier_scores=result.get("per_verifier_scores", {}),
            flagged_reason=result.get("flagged_reason"),
        )
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
    vote: Literal["up", "down"]


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
    threshold: float = Query(0.3, ge=0, le=1),
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
