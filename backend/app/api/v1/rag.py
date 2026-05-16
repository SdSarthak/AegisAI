"""
RAG Intelligence Module — Retrieval-Augmented Generation pipeline for regulatory knowledge queries.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

Pipeline Overview:
    - Uses FAISS as the vector store for efficient similarity search
    - LangChain orchestrates the retrieval and generation steps
    - OpenAI-compatible embeddings convert documents and queries into vectors

Feedback Loop:
    - Users can submit thumbs up/down feedback on RAG responses
    - Feedback is persisted to the RAGFeedback model for quality tracking
    - Negative feedback flags low-quality chunks for admin review

Admin Endpoint:
    - Admins can access a low-quality-chunks endpoint to review and remove
      poorly performing document chunks from the knowledge base

Endpoints:
    POST /rag/query   — Ask a regulatory question grounded in source documents
    GET  /rag/health  — Check if the RAG module is available

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

router = APIRouter()


class RAGQueryRequest(BaseModel):
    question: str


class RAGQueryResponse(BaseModel):
    answer: str
    sources: list[str] = []


@router.post("/query", response_model=RAGQueryResponse)
def query_knowledge_base(
    request: RAGQueryRequest,
    current_user: User = Depends(get_current_user),
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
        sources = [str(doc.metadata.get("source", "")) for doc in result.get("source_documents", [])]
        return RAGQueryResponse(answer=result["result"], sources=sources)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"RAG module not ready: {str(e)}. Run POST /rag/ingest first.",
        )


@router.get("/health", tags=["RAG Intelligence"])
def rag_health():
    """Check if the RAG module is available."""
    return {"module": "rag_intelligence", "status": "available"}