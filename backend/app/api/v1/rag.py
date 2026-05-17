"""
RAG Intelligence API — regulatory knowledge base query endpoint.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

TODO for contributors (high difficulty):
  - Pre-load the EU AI Act, GDPR, ISO 42001, and NIST AI RMF as source documents
  - Add streaming responses via SSE for long answers
"""

import os
import shutil
import tempfile
import time
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.rag_feedback import RAGFeedback
from app.models.rag_query import RagQuery
from app.models.user import SubscriptionTier, User
from app.modules.rag.document_loader import load_documents_from_paths
from app.modules.rag.vector_store import create_vector_store

router = APIRouter()


class RAGQueryRequest(BaseModel):
    question: str


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[str] = []
    answer_id: Optional[str] = None


class RAGIngestResponse(BaseModel):
    """Response returned after a successful document ingestion."""

    files_processed: int
    chunks_created: int
    index_size_bytes: int


class RAGFeedbackRequest(BaseModel):
    answer_id: str
    vote: str  # "up" or "down"


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
    """
    Upload and index regulatory PDF documents into the RAG system.

    Args:
        files (List[UploadFile]): PDF files to ingest into
            the vector database.
        current_user (User): Currently authenticated user.

    Returns:
        RAGIngestResponse: Summary of processed files,
            generated chunks, and vector index size.

    Raises:
        HTTPException: Raised when invalid PDF files are
            uploaded or vector index generation fails.
    """

    pdf_files = [
        f for f in files
        if f.filename and f.filename.lower().endswith(".pdf")
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
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Query the regulatory knowledge base using retrieval-augmented generation.

    Args:
        request (RAGQueryRequest): Request payload containing
            the user's regulatory question.
        current_user (User): Currently authenticated user.
        db (Session): Database session dependency used for
            persisting query history and feedback.

    Returns:
        RAGQueryResponse: Generated answer along with
            supporting source references and answer identifier.

    Raises:
        HTTPException: Raised when the RAG service
            or retrieval pipeline fails.
    """
    try:
        from app.modules.rag.retrieval_chain import get_qa_chain
        from app.core.database import Base

        qa_chain = get_qa_chain()

        t_start = time.monotonic()
        result = qa_chain({"query": request.question})
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
            answer_summary=answer[:200],
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
    """
    Check the availability status of the RAG module and vector index.

    Returns:
        dict: Health status information for the RAG service
            and FAISS vector index.
    """
    from app.modules.rag.vector_store import check_index_exists

    index_loaded = check_index_exists()

    if not index_loaded:
        return {
            "module": "rag_intelligence",
            "status": "unavailable",
            "index_loaded": False,
            "message": (
                "FAISS index not found. "
                "RAG module requires document ingestion before use."
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
):
    """
    Record feedback for a previously generated RAG response.

    Args:
        payload (RAGFeedbackRequest): Request payload containing
            the answer identifier and feedback vote.
        current_user (User): Currently authenticated user.
        db (Session): Database session dependency.

    Returns:
        dict: Confirmation response containing feedback status
            and answer identifier.

    Raises:
        HTTPException: Raised when the referenced answer
            cannot be found.
    """
    fb = db.query(RAGFeedback).filter(
        RAGFeedback.id == payload.answer_id
    ).first()

    if not fb:
        raise HTTPException(
            status_code=404,
            detail="Answer not found",
        )

    if payload.vote == "up":
        fb.thumbs_up = (fb.thumbs_up or 0) + 1
    else:
        fb.thumbs_down = (fb.thumbs_down or 0) + 1

    db.add(fb)
    db.commit()
    db.refresh(fb)

    return {
        "status": "ok",
        "answer_id": fb.id,
    }


@router.get("/low-quality-chunks")
def get_low_quality_chunks(
    threshold: float = 0.3,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve low-quality source chunks based on negative feedback ratios.

    Args:
        threshold (float): Minimum thumbs-down ratio used
            to identify low-quality chunks.
        current_user (User): Currently authenticated user.
        db (Session): Database session dependency.

    Returns:
        dict: Aggregated feedback statistics and identified
            low-quality source chunks.

    Raises:
        HTTPException: Raised when the user does not have
            administrative access permissions.
    """
    try:
        if current_user.subscription_tier != SubscriptionTier.SCALE:
            raise HTTPException(
                status_code=403,
                detail="Admin access required",
            )

    except Exception:
        raise HTTPException(
            status_code=403,
            detail="Admin access required",
        )

    counts: dict[str, dict[str, int]] = {}

    rows = db.query(RAGFeedback).all()

    for r in rows:
        total = (r.thumbs_up or 0) + (r.thumbs_down or 0)

        for chunk in (r.source_chunks or []):

            if chunk not in counts:
                counts[chunk] = {
                    "thumbs_up": 0,
                    "thumbs_down": 0,
                    "total": 0,
                }

            counts[chunk]["thumbs_up"] += (r.thumbs_up or 0)
            counts[chunk]["thumbs_down"] += (r.thumbs_down or 0)
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

    return {
        "threshold": threshold,
        "low_quality_chunks": low_quality,
    }


@router.get("/history")
def get_rag_history(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Retrieve paginated history of the authenticated user's RAG queries.

    Args:
        page (int): Page number for paginated results.
        page_size (int): Maximum number of records per page.
        current_user (User): Currently authenticated user.
        db (Session): Database session dependency.

    Returns:
        dict: Paginated query history including questions,
            answer summaries, source counts, and timestamps.
    """
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