"""
RAG Intelligence API — regulatory knowledge base query endpoint.
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
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.rag_feedback import RAGFeedback
from app.models.user import SubscriptionTier, User
from app.modules.rag.document_loader import load_documents_from_paths
from app.modules.rag.vector_store import create_vector_store
from app.models.rag_query import RagQuery

router = APIRouter()



class RAGQueryRequest(BaseModel):
    question: str


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[str] = []
    answer_id: Optional[str] = None
    groundedness_score: float = Field(0.0, description="Cosine similarity score (0.0 to 1.0) measuring answer groundedness in retrieved chunks.")
    low_confidence: bool = Field(False, description="True if groundedness score falls below the accepted threshold.")


class RAGIngestResponse(BaseModel):
    """Response returned after a successful document ingestion."""

    files_processed: int
    chunks_created: int
    index_size_bytes: int


# ---------------------------------------------------------------------------
# POST /rag/ingest
# ---------------------------------------------------------------------------
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
    Accept one or more PDF uploads, process them through the document loader,
    build (or rebuild) the FAISS vector index, and persist it to
    ``settings.FAISS_INDEX_PATH``.

    **Returns**
    - ``files_processed`` - number of PDFs successfully saved and chunked
    - ``chunks_created``  - total text chunks fed into the vector store
    - ``index_size_bytes`` - on-disk size of the persisted FAISS index

    **Errors**
    - ``400`` if no valid PDF files are supplied
    - ``503`` if the embedding model or FAISS build step fails
    """

    # ── 1. Validate: at least one PDF ─────────────────────────────────────
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

    # ── 2. Save uploads to a temporary directory ──────────────────────────
    tmp_dir = tempfile.mkdtemp(prefix="aegis_ingest_")
    saved_paths: list[str] = []

    try:
        for upload in pdf_files:
            dest = os.path.join(tmp_dir, os.path.basename(upload.filename))
            with open(dest, "wb") as buf:
                shutil.copyfileobj(upload.file, buf)
            saved_paths.append(dest)

        # ── 3. Chunk documents (gives us the accurate chunk count) ────────
        chunks = load_documents_from_paths(saved_paths)
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract any text from the supplied PDFs. "
                       "Ensure the files are not scanned images or password-protected.",
            )

        # ── 4. Build / rebuild FAISS index and persist to disk ────────────
        try:
            create_vector_store(saved_paths)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to build FAISS index: {exc}",
            )

        # ── 5. Calculate on-disk index size ───────────────────────────────
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
        # ── 6. Always clean up the temp directory ─────────────────────────
        shutil.rmtree(tmp_dir, ignore_errors=True)


class RAGIngestResponse(BaseModel):
    """Response returned after a successful document ingestion."""

    files_processed: int
    chunks_created: int
    index_size_bytes: int


# ---------------------------------------------------------------------------
# POST /rag/ingest
# ---------------------------------------------------------------------------
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
    Accept one or more PDF uploads, process them through the document loader,
    build (or rebuild) the FAISS vector index, and persist it to
    ``settings.FAISS_INDEX_PATH``.

    **Returns**
    - ``files_processed`` – number of PDFs successfully saved and chunked
    - ``chunks_created``  – total text chunks fed into the vector store
    - ``index_size_bytes`` – on-disk size of the persisted FAISS index

    **Errors**
    - ``400`` if no valid PDF files are supplied
    - ``503`` if the embedding model or FAISS build step fails
    """

    # ── 1. Validate: at least one PDF ─────────────────────────────────────
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

    # ── 2. Save uploads to a temporary directory ──────────────────────────
    tmp_dir = tempfile.mkdtemp(prefix="aegis_ingest_")
    saved_paths: list[str] = []

    try:
        for upload in pdf_files:
            dest = os.path.join(tmp_dir, os.path.basename(upload.filename))
            with open(dest, "wb") as buf:
                shutil.copyfileobj(upload.file, buf)
            saved_paths.append(dest)

        # ── 3. Chunk documents (gives us the accurate chunk count) ────────
        chunks = load_documents_from_paths(saved_paths)
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract any text from the supplied PDFs. "
                       "Ensure the files are not scanned images or password-protected.",
            )

        # ── 4. Build / rebuild FAISS index and persist to disk ────────────
        try:
            create_vector_store(saved_paths)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to build FAISS index: {exc}",
            )

        # ── 5. Calculate on-disk index size ───────────────────────────────
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
        # ── 6. Always clean up the temp directory ─────────────────────────
        shutil.rmtree(tmp_dir, ignore_errors=True)


@router.post("/query", response_model=RAGQueryResponse)
def query_knowledge_base(
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Query the regulatory knowledge base with a natural language question.

    Runs the question through the RAG pipeline, retrieves relevant chunks
    from the FAISS index, generates a grounded answer, persists feedback
    and query records, and logs metrics to MLflow.

    Args:
        request: Request body containing the question string.
        current_user: The authenticated user extracted from the JWT token.
        db: Database session dependency.

    Returns:
        RAGQueryResponse: Generated answer, source document references,
            and a unique answer_id for feedback submission.

    Raises:
        HTTPException: 503 if the FAISS index is not found or the RAG
            module encounters an error.
    """
    try:
        from app.modules.rag.retrieval_chain import get_qa_chain
        from app.modules.rag.groundedness import compute_groundedness
        from app.core.database import Base

        qa_chain = get_qa_chain()

        t_start = time.monotonic()
        result = qa_chain({"query": request.question})
        latency_ms = (time.monotonic() - t_start) * 1000

        source_docs = result.get("source_documents", [])
        sources = [str(doc.metadata.get("source", "")) for doc in source_docs]
        answer = str(result.get("result", ""))

        # Groundedness Check
        chunk_texts = [str(doc.page_content) for doc in source_docs]
        groundedness_score = compute_groundedness(answer, chunk_texts)
        low_confidence = groundedness_score < 0.70

        # Ensure tables exist on this DB bind (useful for test DB overrides)
        try:
            Base.metadata.create_all(bind=db.get_bind())
        except Exception:
            pass

        # Persist feedback row
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

        # Log to MLflow (non-blocking — failures are swallowed inside log_query)
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
            groundedness_score=groundedness_score,
            low_confidence=low_confidence
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
    """Check if the RAG module is available and the FAISS index is loaded.

    Returns:
        dict: Module name, status (available/unavailable), index_loaded
            flag, and an optional message if the index is missing.
    """
    from app.modules.rag.vector_store import check_index_exists
    
    index_loaded = check_index_exists()
    
    if not index_loaded:
        return {
            "module": "rag_intelligence",
            "status": "unavailable",
            "index_loaded": False,
            "message": "FAISS index not found. RAG module requires document ingestion before use."
        }
    
    return {
        "module": "rag_intelligence",
        "status": "available",
        "index_loaded": True
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
    """Record a thumbs-up or thumbs-down vote for a previously returned answer.

    Args:
        payload: Request body containing answer_id and vote (up or down).
        current_user: The authenticated user extracted from the JWT token.
        db: Database session dependency.

    Returns:
        dict: Status confirmation and the answer_id that was voted on.

    Raises:
        HTTPException: 404 if the answer_id is not found.
    """
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
    """Return source chunks with high negative feedback ratios.

    Aggregates thumbs_up and thumbs_down counts per source chunk across
    all RAGFeedback records and returns chunks where the ratio of
    thumbs_down to total feedback exceeds the threshold. Admin only.

    Args:
        threshold: Minimum thumbs_down ratio to flag a chunk (default: 0.3).
        current_user: The authenticated user extracted from the JWT token.
        db: Database session dependency.

    Returns:
        dict: Threshold value and list of low-quality chunks with their
            thumbs_down count, total feedback, and ratio.

    Raises:
        HTTPException: 403 if user does not have Scale tier access.
    """
    # Admin-only access: restrict to system owners / scale tier
    try:
        if current_user.subscription_tier != SubscriptionTier.SCALE:
            raise HTTPException(status_code=403, detail="Admin access required")
    except Exception:
        raise HTTPException(status_code=403, detail="Admin access required")

    # Aggregate counts per chunk
    counts: dict[str, dict[str, int]] = {}
    rows = db.query(RAGFeedback).all()
    for r in rows:
        total = (r.thumbs_up or 0) + (r.thumbs_down or 0)
        for chunk in (r.source_chunks or []):
            if chunk not in counts:
                counts[chunk] = {"thumbs_up": 0, "thumbs_down": 0, "total": 0}
            counts[chunk]["thumbs_up"] += (r.thumbs_up or 0)
            counts[chunk]["thumbs_down"] += (r.thumbs_down or 0)
            counts[chunk]["total"] += total

    low_quality = []
    for chunk, c in counts.items():
        if c["total"] == 0:
            continue
        ratio = c["thumbs_down"] / c["total"]
        if ratio > threshold:
            low_quality.append({"chunk": chunk, "thumbs_down": c["thumbs_down"], "total": c["total"], "ratio": ratio})

    return {"threshold": threshold, "low_quality_chunks": low_quality}


@router.get("/history")
def get_rag_history(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return paginated list of the current user's past RAG queries.

    Args:
        page: Page number, 1-indexed (default: 1).
        page_size: Number of results per page (default: 10).
        current_user: The authenticated user extracted from the JWT token.
        db: Database session dependency.

    Returns:
        dict: Page info and list of past queries with id, question,
            answer_summary, source_count, and created_at.
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
