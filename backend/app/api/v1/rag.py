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
import time
import uuid
from datetime import datetime
from typing import List, Optional
from typing import List, Literal

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.rag_document import RAGDocument
from app.models.rag_feedback import RAGFeedback
from app.models.rag_query import RagQuery
from app.models.user import SubscriptionTier, User
from app.modules.rag.document_loader import load_documents_from_paths
from app.modules.rag.vector_store import create_vector_store

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


class RAGDocumentResponse(BaseModel):
    id: int
    filename: str
    original_filename: str
    content_type: Optional[str] = None
    file_size_bytes: int
    chunks_count: int
    uploaded_by_id: Optional[int] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RAGDocumentListResponse(BaseModel):
    items: list[RAGDocumentResponse]
    total: int


class RAGDocumentDeleteResponse(BaseModel):
    deleted_document_id: int
    documents_remaining: int
    index_rebuilt: bool
    index_size_bytes: int


def _ensure_storage_dir() -> str:
    os.makedirs(settings.RAG_DOCUMENT_STORAGE_PATH, exist_ok=True)
    return settings.RAG_DOCUMENT_STORAGE_PATH


def _stored_filename(original_filename: str) -> str:
    safe_name = os.path.basename(original_filename).replace(os.sep, "_")
    return f"{uuid.uuid4().hex}_{safe_name}"


def _index_size_bytes() -> int:
    index_path = settings.FAISS_INDEX_PATH
    index_size_bytes = 0
    for fname in ("index.faiss", "index.pkl"):
        fpath = os.path.join(index_path, fname)
        if os.path.exists(fpath):
            index_size_bytes += os.path.getsize(fpath)
    return index_size_bytes


def _rebuild_index_from_documents(documents: list[RAGDocument]) -> int:
    file_paths = [doc.storage_path for doc in documents if os.path.exists(doc.storage_path)]
    if not file_paths:
        shutil.rmtree(settings.FAISS_INDEX_PATH, ignore_errors=True)
        return 0

    create_vector_store(file_paths)
    return _index_size_bytes()


def _current_user_id(current_user: User) -> Optional[int]:
    user_id = getattr(current_user, "id", None)
    return user_id if isinstance(user_id, int) else None


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
    db: Session = Depends(get_db),
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

    storage_dir = _ensure_storage_dir()
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
    pending_documents: list[RAGDocument] = []

    try:
        for upload in pdf_files:
            filename = _stored_filename(upload.filename)
            dest = os.path.join(storage_dir, filename)
            with open(dest, "wb") as buf:
                shutil.copyfileobj(upload.file, buf)
            saved_paths.append(dest)
            pending_documents.append(
                RAGDocument(
                    filename=filename,
                    original_filename=os.path.basename(upload.filename),
                    storage_path=dest,
                    content_type=upload.content_type,
                    file_size_bytes=os.path.getsize(dest),
                    uploaded_by_id=_current_user_id(current_user),
                )
            )

        chunks = load_documents_from_paths(saved_paths)
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Could not extract any text from the supplied PDFs. "
                    "Ensure the files are not scanned images or password-protected."
                ),
            )

        chunks_by_source: dict[str, int] = {path: 0 for path in saved_paths}
        for chunk in chunks:
            source = str(getattr(chunk, "metadata", {}).get("source", ""))
            if source in chunks_by_source:
                chunks_by_source[source] += 1

        for document in pending_documents:
            document.chunks_count = chunks_by_source.get(document.storage_path, 0)
            db.add(document)
        db.flush()

        # ── 4. Build / rebuild FAISS index and persist to disk ────────────
        try:
            all_documents = db.query(RAGDocument).order_by(RAGDocument.id.asc()).all()
            index_size_bytes = _rebuild_index_from_documents(all_documents)
        except Exception as exc:
            db.rollback()
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to build FAISS index: {exc}",
            )

        db.commit()

        return RAGIngestResponse(
            files_processed=len(saved_paths),
            chunks_created=len(chunks),
            index_size_bytes=index_size_bytes,
        )
    finally:
        if db.is_active:
            for path in saved_paths:
                exists_in_db = db.query(RAGDocument).filter(RAGDocument.storage_path == path).first()
                if not exists_in_db and os.path.exists(path):
                    os.remove(path)


@router.get("/documents", response_model=RAGDocumentListResponse)
def list_rag_documents(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List documents currently included in the RAG knowledge base."""
    documents = db.query(RAGDocument).order_by(RAGDocument.created_at.desc()).all()
    return RAGDocumentListResponse(items=documents, total=len(documents))


@router.delete("/documents/{document_id}", response_model=RAGDocumentDeleteResponse)
def delete_rag_document(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove a RAG source document and rebuild the FAISS index."""
    document = db.query(RAGDocument).filter(RAGDocument.id == document_id).first()
    if not document:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="RAG document not found")

    storage_path = document.storage_path
    db.delete(document)
    db.flush()

    remaining_documents = db.query(RAGDocument).order_by(RAGDocument.id.asc()).all()
    try:
        index_size_bytes = _rebuild_index_from_documents(remaining_documents)
    except Exception as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"Failed to rebuild FAISS index: {exc}",
        )

    db.commit()
    if os.path.exists(storage_path):
        try:
            os.remove(storage_path)
        except OSError:
            pass

    return RAGDocumentDeleteResponse(
        deleted_document_id=document_id,
        documents_remaining=len(remaining_documents),
        index_rebuilt=bool(remaining_documents),
        index_size_bytes=index_size_bytes,
    )


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
