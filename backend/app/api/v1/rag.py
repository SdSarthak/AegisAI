"""API for ingesting regulatory documents and querying the RAG index.

The routes here support PDF ingestion, single-shot question answering, and
streaming answers from the regulatory knowledge base.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import logging
import mimetypes
import os
import shutil
import time
import tempfile
from typing import List, Literal, Optional

from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    Query,
    Request,
    UploadFile,
    status,
)
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
logger = logging.getLogger(__name__)


class RAGQueryRequest(BaseModel):
    question: str


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[str] = []
    answer_id: Optional[str] = None
    groundedness_score: float = 0.0
    low_confidence: bool = False
    confidence_tier: Optional[str] = None
    per_verifier_scores: dict[str, float] = {}
    flagged_reason: Optional[str] = None


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
    """Upload PDFs, rebuild the RAG index, and return ingestion stats.

    Args:
        files: One or more PDF uploads to ingest into the local FAISS index.
        current_user: Authenticated user, used to enforce access control.

    Returns:
        RAGIngestResponse with counts for processed files, created chunks,
        and current on-disk index size.

    Raises:
        HTTPException: If the upload is too large, not a valid PDF payload,
            or the index rebuild fails.
    """
    if len(files) > settings.RAG_MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"Too many files. Maximum allowed is {settings.RAG_MAX_FILES_PER_REQUEST}.",
        )

    pdf_files = [
        f for f in files
        if f.filename and mimetypes.guess_type(f.filename)[0] in ("application/pdf", "binary/octet-stream", None)
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

        # ── 3. Chunk documents (gives us the accurate chunk count) ────────
        raw_chunks = load_documents_from_paths(saved_paths)
        
        # Filter out chunks with empty or whitespace-only page_content
        chunks = [
            chunk for chunk in raw_chunks 
            if chunk.page_content and chunk.page_content.strip()
        ]

        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Could not extract any valid text from the supplied PDFs. "
                       "Ensure the files are not scanned images or password-protected.",
            )

        # ── 4. Build / rebuild FAISS index and persist to disk ────────────
        try:
            create_vector_store(chunks) # Pass the extracted Document objects!
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to build FAISS index: {exc}",
            ) from exc

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
    """Answer a compliance question using the current vector store.

    Args:
        request: Query payload containing the user's compliance question.
        current_user: Authenticated user asking the question.
        db: Active database session used to persist the generated answer.

    Returns:
        RAGQueryResponse containing the answer text, source references, and
        the persisted answer ID.

    Raises:
        HTTPException: If the vector store is unavailable or the RAG pipeline
            fails during retrieval or generation.
    """
    try:
        from app.core.database import Base
        from app.modules.rag.retrieval_chain import get_qa_chain

        qa_chain = get_qa_chain()
        result = qa_chain({"query": request.question})
        source_docs = result.get("source_documents", [])
        sources = [str(doc.metadata.get("source", "")) for doc in source_docs]

        # Ensure tables exist on this DB bind (useful for test DB overrides)
        try:
            Base.metadata.create_all(bind=db.get_bind())
        except Exception:
            logger.debug("Skipping table bootstrap because the DB bind is unavailable")

        # Persist an initial RAGFeedback row to capture the answer and contributing chunks
        feedback = RAGFeedback(
            question=request.question,
            answer=str(result.get("result", "")),
            source_chunks=sources,
        )
        db.add(feedback)
        db.commit()
        db.refresh(feedback)
        answer_id = feedback.id

        return RAGQueryResponse(
            answer=result["result"],
            sources=sources,
            answer_id=answer_id,
            groundedness_score=float(result.get("groundedness_score", 0.0)),
            low_confidence=bool(result.get("low_confidence", False)),
            confidence_tier=result.get("confidence_tier"),
            per_verifier_scores=dict(result.get("per_verifier_scores", {})),
            flagged_reason=result.get("flagged_reason"),
        )
    except FileNotFoundError as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(e),
        ) from e
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"RAG module error: {str(e)}",
        ) from e


# ---------------------------------------------------------------------------
# POST /rag/query/stream  —  Server-Sent Events
# ---------------------------------------------------------------------------
@router.post(
    "/query/stream",
    summary="Stream a regulatory answer token-by-token (SSE)",
    tags=["RAG Intelligence"],
    responses={
        200: {
            "description": (
                "Server-Sent Events stream. Emits one `meta` event with "
                "citations and answer_id, then zero or more `token` events "
                "with answer deltas, then a terminal `done` event. On "
                "failure an `error` event is emitted before `done`."
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
):
    """Stream a regulatory answer token-by-token as Server-Sent Events.

    Args:
        request: Incoming HTTP request used for SSE lifecycle handling.
        payload: Query payload containing the user's compliance question.
        current_user: Authenticated user requesting the streamed answer.
        db: Active database session used to persist the generated answer.

    Returns:
        StreamingResponse that emits meta, token, error, and done events.

    Raises:
        HTTPException: If the vector store cannot be loaded.
    """
    try:
        vector_store = load_vector_store()
    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        ) from exc

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
            # Prevent intermediary buffering (nginx in particular) from
            # holding back tokens until the response is "done".
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
            "Connection": "keep-alive",
        },
    )


@router.get("/health", tags=["RAG Intelligence"])
def rag_health():
    """Check whether the RAG module is available.

    Returns:
        A small status payload indicating whether the FAISS index is loaded
        and the RAG module can answer queries.
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
    vote: Literal["up", "down"]


@router.post("/feedback")
def rag_feedback(
    payload: RAGFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record feedback for a previously generated answer.

    Args:
        payload: Feedback payload containing the answer ID and vote.
        current_user: Authenticated user submitting the feedback.
        db: Active database session.

    Returns:
        Confirmation payload with the stored answer ID.

    Raises:
        HTTPException: If the answer cannot be found.
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
    threshold: float = Query(0.3, ge=0, le=1),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Aggregate feedback by source chunk and return low-quality candidates.

    Args:
        threshold: Downvote ratio above which a chunk is considered low
            quality.
        current_user: Authenticated user requesting the quality report.
        db: Active database session.

    Returns:
        A report containing the configured threshold and the chunk list that
        exceeds it.

    Raises:
        HTTPException: If the caller does not have the required admin tier.
    """
    # Admin-only access: restrict to system owners / scale tier
    try:
        if current_user.subscription_tier != SubscriptionTier.SCALE:
            raise HTTPException(status_code=403, detail="Admin access required")
    except Exception:
        raise HTTPException(status_code=403, detail="Admin access required") from None

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
    """Return the current user's paginated RAG query history.

    Args:
        page: Page number to retrieve, starting at 1.
        page_size: Number of history records per page.
        current_user: Authenticated user whose history should be returned.
        db: Active database session.

    Returns:
        A paginated payload containing the user's prior RAG queries and
        answer summaries.
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
