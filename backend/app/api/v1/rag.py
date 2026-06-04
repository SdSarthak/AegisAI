"""
RAG Intelligence API — regulatory knowledge base query endpoint.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import os
import shutil
import tempfile
import time
from typing import List, Literal, Optional

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.rag_feedback import RAGFeedback
from app.models.rag_query import RagQuery
from app.models.user import SubscriptionTier, User
from app.modules.llm.llm_client import LLMClient
from app.modules.rag.document_loader import load_documents_from_paths
from app.modules.rag.streaming import stream_rag_answer
from app.modules.rag.vector_store import create_vector_store, load_vector_store

router = APIRouter()


class RAGQueryRequest(BaseModel):
    question: str


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[str] = []
    answer_id: Optional[str] = None
    groundedness_score: Optional[float] = None
    low_confidence: bool = False


class RAGIngestResponse(BaseModel):
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
    """Accept one or more PDF uploads and process them."""
    if len(files) > settings.RAG_MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Too many files. Maximum allowed is {settings.RAG_MAX_FILES_PER_REQUEST}.",
        )

    pdf_files: list[UploadFile] = []

    for upload in files:
        filename = upload.filename or ""
        content_type = upload.content_type or ""

        is_pdf_extension = filename.lower().endswith(".pdf")
        is_pdf_content_type = content_type in (
            "application/pdf",
            "binary/octet-stream",
            "",
        )

        if not is_pdf_extension or not is_pdf_content_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Only PDF files are supported.",
            )

        pdf_files.append(upload)

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
                f"Total upload size exceeds the maximum budget of "
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
    start_time = time.monotonic()

    try:
        from app.core.database import Base
        from app.modules.rag.retrieval_chain import get_qa_chain

        qa_chain = get_qa_chain()
        result = qa_chain({"query": request.question})

        source_docs = result.get("source_documents", [])
        sources = [str(doc.metadata.get("source", "")) for doc in source_docs]
        _latency_ms = int((time.monotonic() - start_time) * 1000)

        try:
            Base.metadata.create_all(bind=db.get_bind())
        except Exception:
            pass

        feedback = RAGFeedback(
            question=request.question,
            answer=str(result.get("result", "")),
            source_chunks=sources,
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)

        return RAGQueryResponse(
            answer=str(result.get("result", "")),
            sources=sources,
            answer_id=str(feedback.id),
            groundedness_score=result.get("groundedness_score"),
            low_confidence=bool(result.get("low_confidence", False)),
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


@router.post(
    "/query/stream",
    summary="Stream a regulatory answer token-by-token (SSE)",
    tags=["RAG Intelligence"],
)
async def query_knowledge_base_stream(
    request: Request,
    payload: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Stream a regulatory answer as Server-Sent Events."""
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
def rag_health():
    """Check if the RAG module is available."""
    from app.modules.rag.vector_store import check_index_exists

    index_loaded = check_index_exists()

    if not index_loaded:
        return {
            "module": "rag_intelligence",
            "status": "unavailable",
            "index_loaded": False,
            "message": "FAISS index not found. RAG module requires document ingestion before use.",
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
    """Record a thumbs-up or thumbs-down for a previously returned answer."""
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
    """Admin endpoint: aggregate feedback by source chunk and return low-quality candidates."""
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