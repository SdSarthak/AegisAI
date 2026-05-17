"""
RAG Intelligence API — ``backend/app/api/v1/rag.py``
=====================================================

FastAPI router exposing AegisAI's Retrieval-Augmented Generation (RAG)
pipeline under the ``/api/v1/rag`` prefix.

Users can upload regulatory PDFs, query them in natural language, and receive
answers grounded in indexed source documents — not solely in LLM training data.
The module also tracks per-answer feedback to surface low-quality chunks for
re-ingestion.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

Endpoints
---------
+--------+---------------------------+------------+----------------------------------------------+
| Method | Path                      | Auth       | Description                                  |
+========+===========================+============+==============================================+
| POST   | /rag/ingest               | Required   | Upload PDFs → chunk → rebuild FAISS index    |
+--------+---------------------------+------------+----------------------------------------------+
| POST   | /rag/query                | Required   | Ask a regulatory question; returns answer    |
|        |                           |            | grounded in indexed source documents         |
+--------+---------------------------+------------+----------------------------------------------+
| GET    | /rag/health               | None       | Returns FAISS index availability status      |
+--------+---------------------------+------------+----------------------------------------------+
| POST   | /rag/feedback             | Required   | Thumbs-up / thumbs-down on a returned answer |
+--------+---------------------------+------------+----------------------------------------------+
| GET    | /rag/low-quality-chunks   | SCALE only | Chunks where thumbs_down ratio > threshold   |
+--------+---------------------------+------------+----------------------------------------------+

RAG Query Pipeline  (POST /rag/query)
--------------------------------------
::

    User question (string)
        │
        ▼
    retrieval_chain.get_qa_chain()
        │  LangChain RetrievalQA chain backed by:
        │    • FAISS vector store  (from settings.FAISS_INDEX_PATH)
        │    • OpenAI-compatible embeddings
        │    • Configured LLM
        ▼
    Top-K retrieved document chunks  (semantic nearest-neighbour)
        │
        ▼
    LLM  (generates answer grounded in retrieved chunks)
        │
        ▼
    RAGQueryResponse
        ├── answer     — LLM-generated regulatory answer
        ├── sources    — list of source document paths
        └── answer_id  — UUID of the persisted RAGFeedback row

Document Ingestion Pipeline  (POST /rag/ingest)
------------------------------------------------
::

    Uploaded PDF files  (multipart/form-data)
        │
        ▼
    Saved to a temp directory  (cleaned up automatically via try/finally)
        │
        ▼
    document_loader.load_documents_from_paths()
        │  Chunks PDFs into overlapping text segments
        ▼
    vector_store.create_vector_store()
        │  Embeds chunks → persists FAISS index to settings.FAISS_INDEX_PATH
        ▼
    RAGIngestResponse
        ├── files_processed  — PDFs successfully chunked
        ├── chunks_created   — total text chunks embedded
        └── index_size_bytes — on-disk size of index.faiss + index.pkl

Feedback & Quality Loop
-----------------------
Every ``POST /rag/query`` call persists a ``RAGFeedback`` row capturing the
question, generated answer, and contributing source chunks.

Users vote via ``POST /rag/feedback`` (``"up"`` or ``"down"``).

Admins (``SubscriptionTier.SCALE``) query ``GET /rag/low-quality-chunks`` to
surface chunks where ``thumbs_down / total_feedback > threshold`` — indicating
the chunk is misleading or outdated and should be re-ingested.

HTTP Error Codes
----------------
- ``400`` — No valid PDFs uploaded, or PDFs contain no extractable text
- ``403`` — ``/low-quality-chunks`` accessed by a non-SCALE user
- ``404`` — ``answer_id`` not found in ``POST /rag/feedback``
- ``503`` — FAISS index not yet built (``/query``), or index build failed (``/ingest``)

Configuration  (``backend/.env`` → ``app.core.config.Settings``)
-----------------------------------------------------------------
::

    FAISS_INDEX_PATH=./data/faiss_index    # dir containing index.faiss + index.pkl
    LLM_API_KEY=your-key                   # or "ollama" for local inference
    LLM_BASE_URL=https://api.openai.com/v1 # OpenAI-compatible endpoint
    LLM_MODEL=gpt-4o-mini                  # model identifier

Usage Examples
--------------
::

    # Ingest the EU AI Act PDF
    curl -X POST http://localhost:8000/api/v1/rag/ingest \
         -H "Authorization: Bearer <token>" \
         -F "files=@eu_ai_act.pdf"

    # Ask a regulatory question
    curl -X POST http://localhost:8000/api/v1/rag/query \
         -H "Authorization: Bearer <token>" \
         -H "Content-Type: application/json" \
         -d '{"question": "Does my CV-screening tool qualify as high-risk under the EU AI Act?"}'

    # Vote on an answer
    curl -X POST http://localhost:8000/api/v1/rag/feedback \
         -H "Authorization: Bearer <token>" \
         -H "Content-Type: application/json" \
         -d '{"answer_id": "<uuid>", "vote": "up"}'

Open TODOs
----------
- Pre-load EU AI Act, GDPR, ISO 42001, and NIST AI RMF as built-in source documents
- Integrate MLflow experiment tracking via ``app.modules.rag.ml_flow``
- Add streaming responses via Server-Sent Events (SSE) for long answers

See Also
--------
- ``app.modules.rag.retrieval_chain`` — get_qa_chain() LangChain assembly
- ``app.modules.rag.document_loader`` — PDF chunking logic
- ``app.modules.rag.vector_store``    — FAISS index build and health check
- ``app.modules.rag.ml_flow``         — MLflow tracking helpers
- ``app.models.rag_feedback``         — RAGFeedback SQLAlchemy ORM model
- ``app.core.config``                 — Settings and FAISS_INDEX_PATH
"""

import os
import shutil
import tempfile
from typing import List, Optional

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.rag_feedback import RAGFeedback
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
    """
    Ask a regulatory question and get an answer grounded in source documents.

    Example questions:
    - "Does my CV-screening tool qualify as high-risk under the EU AI Act?"
    - "What are the transparency requirements for chatbots?"
    """
    try:
        from app.modules.rag.retrieval_chain import get_qa_chain
        from app.core.database import Base

        qa_chain = get_qa_chain()
        result = qa_chain({"query": request.question})
        source_docs = result.get("source_documents", [])
        sources = [str(doc.metadata.get("source", "")) for doc in source_docs]

        # Ensure tables exist on this DB bind (useful for test DB overrides)
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
    """Check if the RAG module is available."""
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
