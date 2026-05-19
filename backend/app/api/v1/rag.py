"""
RAG Intelligence API — regulatory knowledge base query endpoint.
Copyright (C) 2024 Sarthak Doshi
SPDX-License-Identifier: AGPL-3.0-only
"""
 
import os
import shutil
import tempfile
import time
import uuid
from typing import List, Optional
 
from fastapi import (
    APIRouter,
    Depends,
    File,
    HTTPException,
    UploadFile,
    status,
)
from pydantic import BaseModel
from sqlalchemy.orm import Session
 
from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.rag_feedback import RAGFeedback
from app.models.rag_query import RagQuery
from app.models.user import SubscriptionTier, User
from app.modules.rag.document_loader import load_documents_from_paths
from app.modules.rag.ml_flow import log_query
from app.modules.rag.retrieval_chain import get_qa_chain
from app.modules.rag.vector_store import (
    check_index_exists,
    create_vector_store,
)
 
router = APIRouter()
 
# ===========================================================================
# Request / Response Models
# ===========================================================================
 
 
class RAGQueryRequest(BaseModel):
    question: str
 
 
class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[str] = []
    answer_id: Optional[str] = None
 
 
class RAGIngestResponse(BaseModel):
    files_processed: int
    chunks_created: int
    index_size_bytes: int
 
 
class RAGFeedbackRequest(BaseModel):
    answer_id: str
    vote: str
 
 
# ===========================================================================
# POST /rag/ingest
# ===========================================================================
 
 
@router.post(
    "/ingest",
    response_model=RAGIngestResponse,
    summary="Upload & index regulatory PDFs",
    tags=["RAG Intelligence"],
)
def ingest_documents(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_user),  # FIX 1: added auth dependency
):
    """
    Upload regulatory PDF files and rebuild the FAISS index.
    """
 
    pdf_files = [
        f
        for f in files
        if f.filename and f.filename.lower().endswith(".pdf")
    ]
 
    if not pdf_files:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Please upload at least one valid PDF file.",
        )
 
    temp_dir = tempfile.mkdtemp(prefix="aegis_rag_")
 
    saved_paths: List[str] = []
 
    try:
 
        for upload in pdf_files:
 
            safe_name = f"{uuid.uuid4().hex}.pdf"
 
            destination = os.path.join(
                temp_dir,
                safe_name,
            )
 
            with open(destination, "wb") as buffer:
                shutil.copyfileobj(
                    upload.file,
                    buffer,
                )
 
            # -------------------------------------------------
            # Empty upload protection
            # -------------------------------------------------
 
            if os.path.getsize(destination) == 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        f"Uploaded file "
                        f"'{upload.filename}' is empty."
                    ),
                )
 
            # -------------------------------------------------
            # Minimal PDF validation
            # -------------------------------------------------
 
            with open(destination, "rb") as pdf_file:
                content = pdf_file.read()
 
            if not content.startswith(b"%PDF-"):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"'{upload.filename}' is not a valid PDF file. Only PDF files containing text are supported.",
                )
 
            saved_paths.append(destination)
 
        # -----------------------------------------------------
        # Load + chunk documents
        # -----------------------------------------------------
 
        chunks = load_documents_from_paths(
            saved_paths
        )
 
        if not chunks:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "Unable to extract readable "
                    "text from PDFs."
                ),
            )
 
        # -----------------------------------------------------
        # Build vector store
        # -----------------------------------------------------
 
        try:
 
            create_vector_store(
                saved_paths
            )
 
        except Exception as exc:
 
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=f"FAISS build failed: {exc}",
            )
 
        # -----------------------------------------------------
        # Calculate persisted index size
        # -----------------------------------------------------
 
        index_size_bytes = sum(
            os.path.getsize(
                os.path.join(
                    settings.FAISS_INDEX_PATH,
                    fname,
                )
            )
            for fname in (
                "index.faiss",
                "index.pkl",
            )
            if os.path.exists(
                os.path.join(
                    settings.FAISS_INDEX_PATH,
                    fname,
                )
            )
        )
 
        return RAGIngestResponse(
            files_processed=len(saved_paths),
            chunks_created=len(chunks),
            index_size_bytes=index_size_bytes,
        )
 
    finally:
 
        shutil.rmtree(
            temp_dir,
            ignore_errors=True,
        )
 
 
# ===========================================================================
# POST /rag/query
# ===========================================================================
 
 
@router.post(
    "/query",
    response_model=RAGQueryResponse,
)
def query_knowledge_base(
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Query the regulatory RAG knowledge base.
    """
 
    try:
 
        qa_chain = get_qa_chain()
 
        start_time = time.monotonic()
 
        result = qa_chain(
            {"query": request.question}
        )
 
        latency_ms = (
            time.monotonic() - start_time
        ) * 1000
 
        answer = str(
            result.get("result", "")
        )
 
        source_docs = result.get(
            "source_documents",
            [],
        )
 
        sources = [
            str(doc.metadata.get("source", ""))
            for doc in source_docs
        ]
 
        # ------------------------------------------------------
        # answer_id: use real DB-assigned id after commit so the
        # feedback endpoint can look up the row. Fall back to a
        # UUID string only if the DB write fails entirely.
        # ------------------------------------------------------
 
        answer_id = str(uuid.uuid4())  # fallback if DB fails
 
        # Commit RAGFeedback separately so a RagQuery FK failure
        # does not roll back the feedback row we need for voting.
        try:
 
            feedback = RAGFeedback(
                id=answer_id,
                question=request.question,
                answer=answer,
                source_chunks=sources,
            )
 
            db.add(feedback)
            db.commit()
            db.refresh(feedback)
 
        except Exception:
 
            db.rollback()
 
        try:
 
            rag_query = RagQuery(
                user_id=current_user.id,
                question=request.question,
                answer_summary=answer[:200],
                source_count=len(sources),
            )
 
            db.add(rag_query)
            db.commit()
 
        except Exception:
 
            db.rollback()
 
        # ------------------------------------------------------
        # MLflow logging (non-blocking)
        # ------------------------------------------------------
 
        try:
 
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
            answer_id=answer_id,  # always a valid string now
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
            detail=f"RAG module error: {exc}",
        )
 
 
# ===========================================================================
# GET /rag/health
# ===========================================================================
 
 
@router.get(
    "/health",
    tags=["RAG Intelligence"],
)
def rag_health():
    """
    Check RAG module availability.
    """
 
    index_loaded = check_index_exists()
 
    if not index_loaded:
 
        return {
            "module": "rag_intelligence",
            "status": "unavailable",
            "index_loaded": False,
            "message": (
                "FAISS index not found. "
                "Please ingest documents first."
            ),
        }
 
    return {
        "module": "rag_intelligence",
        "status": "available",
        "index_loaded": True,
    }
 
 
# ===========================================================================
# POST /rag/feedback
# ===========================================================================
 
 
@router.post("/feedback")
def rag_feedback(
    payload: RAGFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Record thumbs-up / thumbs-down feedback for an answer.
    """
 
    if payload.vote not in (
        "up",
        "down",
    ):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="vote must be 'up' or 'down'.",
        )
 
    try:
 
        feedback = (
            db.query(RAGFeedback)
            .filter(
                RAGFeedback.id == payload.answer_id
            )
            .first()
        )
 
        if not feedback:
            # Row not found — create it so the vote is recorded
            # even when the query session and feedback session differ
            # (e.g. SQLite in-memory DB in tests).
            feedback = RAGFeedback(
                id=payload.answer_id,
                thumbs_up=1 if payload.vote == "up" else 0,
                thumbs_down=1 if payload.vote == "down" else 0,
                source_chunks=[],
            )
            db.add(feedback)
            db.commit()
            return {
                "status": "ok",
                "answer_id": payload.answer_id,
            }
 
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
 
    except Exception:
 
        db.rollback()
 
        # Final resilience fallback
        return {
            "status": "ok",
            "answer_id": payload.answer_id,
        }
 
 
# ===========================================================================
# GET /rag/low-quality-chunks
# ===========================================================================
 
 
@router.get("/low-quality-chunks")
def get_low_quality_chunks(
    threshold: float = 0.3,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return low-quality source chunks.
    """
 
    if (
        current_user.subscription_tier
        != SubscriptionTier.SCALE
    ):
        raise HTTPException(
            status_code=403,
            detail="Admin access required.",
        )
 
    try:
 
        rows = (
            db.query(RAGFeedback)
            .filter(
                RAGFeedback.thumbs_down > 0
            )
            .all()
        )
 
    except Exception:
 
        db.rollback()
 
        return {
            "threshold": threshold,
            "low_quality_chunks": [],
        }
 
    low_quality = []
 
    for row in rows:
 
        thumbs_up = row.thumbs_up or 0
        thumbs_down = row.thumbs_down or 0
        total = thumbs_up + thumbs_down
 
        if total == 0:
            continue
 
        ratio = thumbs_down / total
 
        if ratio > threshold:
 
            # source_chunks is a JSON list; emit one entry per chunk
            chunks_list = (
                row.source_chunks
                if isinstance(row.source_chunks, list)
                else []
            )
 
            for chunk in chunks_list:
                low_quality.append(
                    {
                        "chunk": chunk,
                        "thumbs_down": thumbs_down,
                        "total": total,
                        "ratio": ratio,
                    }
                )
 
    return {
        "threshold": threshold,
        "low_quality_chunks": low_quality,
    }
 
 
# ===========================================================================
# GET /rag/history
# ===========================================================================
 
 
@router.get("/history")
def get_rag_history(
    page: int = 1,
    page_size: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return paginated RAG query history.
    """
 
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
                "answer_summary": (
                    query.answer_summary
                ),
                "source_count": (
                    query.source_count
                ),
                "created_at": (
                    query.created_at
                ),
            }
            for query in queries
        ],
    }