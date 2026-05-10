"""
RAG Intelligence API — regulatory knowledge base query endpoint.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

TODO for contributors (high difficulty):
  - Pre-load the EU AI Act, GDPR, ISO 42001, and NIST AI RMF as source documents
  - Add a POST /rag/ingest endpoint for uploading custom regulatory PDFs
  - Integrate MLflow tracking from modules/rag/ml_flow.py
  - Add streaming responses via SSE for long answers
"""

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from app.core.security import get_current_user
from app.models.user import User
from app.core.database import get_db
from sqlalchemy.orm import Session
from app.models.rag_feedback import RAGFeedback
from app.models.user import SubscriptionTier
from typing import Optional

router = APIRouter()


class RAGQueryRequest(BaseModel):
    question: str


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[str] = []
    answer_id: Optional[str] = None


@router.post("/query", response_model=RAGQueryResponse)
def query_knowledge_base(
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Ask a regulatory question and get an answer grounded in source documents.

    Example questions:
    - "Does my CV-screening tool qualify as high-risk under the EU AI Act?"
    - "What are the transparency requirements for chatbots?"
    """
    try:
        from app.modules.rag.retrieval_chain import get_qa_chain
        qa_chain = get_qa_chain()
        result = qa_chain({"query": request.question})
        source_docs = result.get("source_documents", [])
        sources = [str(doc.metadata.get("source", "")) for doc in source_docs]

        # Ensure tables exist on this DB bind (useful for test DB overrides)
        from app.core.database import Base
        try:
            Base.metadata.create_all(bind=db.get_bind())
        except Exception:
            # best-effort: ignore if bind not available
            pass

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

        return RAGQueryResponse(answer=result["result"], sources=sources, answer_id=answer_id)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"RAG module not ready: {str(e)}. Run POST /rag/ingest first.",
        )


@router.get("/health", tags=["RAG Intelligence"])
def rag_health():
    """Check if the RAG module is available."""
    return {"module": "rag_intelligence", "status": "available"}


class RAGFeedbackRequest(BaseModel):
    answer_id: str
    vote: str  # "up" or "down"


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
    threshold: float = 0.3,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Admin endpoint: aggregate feedback by source chunk and return low-quality candidates.

    A chunk is considered low-quality when thumbs_down / total_feedback > threshold.
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
