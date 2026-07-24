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
import mimetypes

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
from pydantic import BaseModel, Field
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
from app.modules.rag.vector_store import (
    create_vector_store,
    load_vector_store,
)

router = APIRouter()


# ============================================================================
# REQUEST / RESPONSE MODELS
# ============================================================================


class RAGQueryRequest(BaseModel):
    question: str = Field(..., min_length=1)


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[str] = []
    answer_id: Optional[str] = None
    groundedness_score: float = 0.0
    low_confidence: bool = False
   

class RAGIngestResponse(BaseModel):
    files_processed: int
    chunks_created: int
    index_size_bytes: int


class RAGFeedbackRequest(BaseModel):
    answer_id: str
    vote: Literal["up", "down"]


# ============================================================================
# POST /rag/ingest
# ============================================================================


@router.post(
    "/ingest",
    response_model=RAGIngestResponse,
    summary="Upload and index regulatory PDFs",
    tags=["RAG Intelligence"],
)
def ingest_documents(
    files: List[UploadFile] = File(
        ...,
        description="One or more PDF files to ingest",
    ),
    current_user: User = Depends(get_current_user),
):
    """Upload PDF files and rebuild the FAISS vector index."""

    if len(files) > settings.RAG_MAX_FILES_PER_REQUEST:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=(
                f"Too many files. Maximum allowed is "
                f"{settings.RAG_MAX_FILES_PER_REQUEST}."
            ),
        )

    pdf_files = [
        file
        for file in files
        if file.filename
        and (
            mimetypes.guess_type(file.filename)[0]
            in (
                "application/pdf",
                "binary/octet-stream",
                None,
            )
        )
    ]

    if not pdf_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=(
                "No valid PDF files supplied. "
                "Please upload files with a .pdf extension."
            ),
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
        # Save uploaded files temporarily
        for upload in pdf_files:
            destination = os.path.join(
                tmp_dir,
                os.path.basename(upload.filename),
            )

            with open(destination, "wb") as buffer:
                shutil.copyfileobj(upload.file, buffer)

            saved_paths.append(destination)

        # Load and split documents into chunks
        raw_chunks = load_documents_from_paths(saved_paths)

        chunks = [
            chunk
            for chunk in raw_chunks
            if chunk.page_content
            and chunk.page_content.strip()
        ]

        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Could not extract valid text from the supplied PDFs. "
                    "Ensure the files are not scanned images or password-protected."
                ),
            )

        # Build FAISS vector store
        try:
            create_vector_store(chunks)
        except Exception as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"Failed to build FAISS index: {exc}",
            )

        # Calculate FAISS index size
        index_path = settings.FAISS_INDEX_PATH
        index_size_bytes = 0

        for filename in ("index.faiss", "index.pkl"):
            file_path = os.path.join(index_path, filename)

            if os.path.exists(file_path):
                index_size_bytes += os.path.getsize(file_path)

        return RAGIngestResponse(
            files_processed=len(saved_paths),
            chunks_created=len(chunks),
            index_size_bytes=index_size_bytes,
        )

    finally:
        # Always remove temporary files
        shutil.rmtree(
            tmp_dir,
            ignore_errors=True,
        )


# ============================================================================
# POST /rag/query
# ============================================================================


@router.post(
    "/query",
    response_model=RAGQueryResponse,
)
def query_knowledge_base(
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ask a regulatory question and return a grounded answer."""

    try:
        from app.modules.rag.retrieval_chain import get_qa_chain

        qa_chain = get_qa_chain()

        result = qa_chain(
            {
                "query": request.question,
            }
        )

        answer = str(
            result.get(
                "result",
                "",
            )
        )

        source_docs = result.get(
            "source_documents",
            [],
        )

        sources = [
            str(
                doc.metadata.get(
                    "source",
                    "",
                )
            )
            for doc in source_docs
        ]

        # ------------------------------------------------------------
        # Save answer feedback record
        # ------------------------------------------------------------

        feedback = RAGFeedback(
            question=request.question,
            answer=answer,
            source_chunks=sources,
        )

        db.add(feedback)

        db.commit()

        db.refresh(feedback)

        answer_id = str(feedback.id)

        # ------------------------------------------------------------
        # Save RAG query history
        # ------------------------------------------------------------

        rag_query = RagQuery(
            user_id=current_user.id,
            question=request.question,
            answer_summary=answer[:500],
            source_count=len(sources),
        )

        db.add(rag_query)

        db.commit()

        # ------------------------------------------------------------
        # Return response
        # ------------------------------------------------------------

        return RAGQueryResponse(
            answer=answer,
            sources=sources,
            answer_id=answer_id,
            groundedness_score=0.0,
            low_confidence=False,
        )

    except FileNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    except HTTPException:
        raise

    except Exception as exc:
        db.rollback()

        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"RAG module error: {str(exc)}",
        )


# ============================================================================
# POST /rag/query/stream
# ============================================================================


@router.post(
    "/query/stream",
    summary="Stream a regulatory answer token-by-token",
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

    retriever = vector_store.as_retriever(
        search_kwargs={
            "k": 5,
        }
    )

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


# ============================================================================
# GET /rag/health
# ============================================================================


@router.get(
    "/health",
    tags=["RAG Intelligence"],
)
def rag_health():
    """Check whether the RAG module is available."""

    from app.modules.rag.vector_store import check_index_exists

    index_loaded = check_index_exists()

    if not index_loaded:
        return {
            "module": "rag_intelligence",
            "status": "unavailable",
            "index_loaded": False,
            "message": (
                "FAISS index not found. "
                "RAG module requires document ingestion first."
            ),
        }

    return {
        "module": "rag_intelligence",
        "status": "available",
        "index_loaded": True,
    }


# ============================================================================
# POST /rag/feedback
# ============================================================================


@router.post(
    "/feedback",
)
def rag_feedback(
    payload: RAGFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Record thumbs-up or thumbs-down feedback."""

    answer_id = payload.answer_id
    
    feedback = (
        db.query(RAGFeedback)
        .filter(
            RAGFeedback.id == answer_id,
        )
        .first()
    )

    if not feedback:
        raise HTTPException(
            status_code=404,
            detail="Answer not found.",
        )

    if payload.vote == "up":
        feedback.thumbs_up = (
            feedback.thumbs_up or 0
        ) + 1

    else:
        feedback.thumbs_down = (
            feedback.thumbs_down or 0
        ) + 1

    db.add(feedback)

    db.commit()

    db.refresh(feedback)

    return {
        "status": "ok",
        "answer_id": feedback.id,
    }


# ============================================================================
# GET /rag/low-quality-chunks
# ============================================================================


@router.get(
    "/low-quality-chunks",
)
def get_low_quality_chunks(
    threshold: float = Query(
        0.3,
        ge=0,
        le=1,
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return source chunks receiving poor feedback."""

    if current_user.subscription_tier != SubscriptionTier.SCALE:
        raise HTTPException(
            status_code=403,
            detail="Admin access required.",
        )

    counts: dict[str, dict[str, int]] = {}

    rows = db.query(
        RAGFeedback
    ).all()

    for feedback in rows:
        total = (
            feedback.thumbs_up or 0
        ) + (
            feedback.thumbs_down or 0
        )

        for chunk in (
            feedback.source_chunks or []
        ):
            if chunk not in counts:
                counts[chunk] = {
                    "thumbs_up": 0,
                    "thumbs_down": 0,
                    "total": 0,
                }

            counts[chunk]["thumbs_up"] += (
                feedback.thumbs_up or 0
            )

            counts[chunk]["thumbs_down"] += (
                feedback.thumbs_down or 0
            )

            counts[chunk]["total"] += total

    low_quality = []

    for chunk, count in counts.items():
        if count["total"] == 0:
            continue

        ratio = (
            count["thumbs_down"]
            / count["total"]
        )

        if ratio > threshold:
            low_quality.append(
                {
                    "chunk": chunk,
                    "thumbs_down": count["thumbs_down"],
                    "total": count["total"],
                    "ratio": ratio,
                }
            )

    return {
        "threshold": threshold,
        "low_quality_chunks": low_quality,
    }


# ============================================================================
# GET /rag/history
# ============================================================================


@router.get(
    "/history",
)
def get_rag_history(
    page: int = Query(
        1,
        ge=1,
    ),
    page_size: int = Query(
        10,
        ge=1,
        le=100,
    ),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return the current user's paginated RAG query history."""

    offset = (
        page - 1
    ) * page_size

    queries = (
        db.query(RagQuery)
        .filter(
            RagQuery.user_id
            == current_user.id
        )
        .order_by(
            RagQuery.created_at.desc()
        )
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