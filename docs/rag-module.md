## Maintaining Knowledge Base Quality

### Low-quality chunk aggregation

The API provides an administrative endpoint to surface RAG chunks that receive low user feedback (thumbs-down). Use this to decide which chunks to re-ingest, repair, or remove from the FAISS index.

- GET `/api/v1/rag/low-quality-chunks?threshold=0.3`
  - Protected: admin/system-owner only (users on the `scale` subscription tier).
  - Returns a list of chunk identifiers (the `source` metadata saved during ingestion) that have a thumbs-down ratio greater than `threshold`.

Workflow:

1. Query the RAG endpoint as usual: `POST /api/v1/rag/query` — the server stores the returned `answer_id` and the list of contributing chunk sources.
2. Have users submit feedback: `POST /api/v1/rag/feedback` with `{"answer_id": "...", "vote": "down"}`.
3. Run the aggregation endpoint: `GET /api/v1/rag/low-quality-chunks` to get candidate chunks for re-ingestion.

The endpoint returns objects with `chunk`, `thumbs_down`, `total` and `ratio` fields to help prioritize remediation.
# RAG Intelligence Module

The RAG (Retrieval-Augmented Generation) module lets you ask natural language questions about AI regulations and receive grounded answers with source citations — rather than relying on an LLM's potentially outdated or hallucinated knowledge.

---

## Table of Contents

- [How it works](#how-it-works)
- [Current status](#current-status)
- [Ingesting regulatory documents](#ingesting-regulatory-documents)
- [Querying the knowledge base](#querying-the-knowledge-base)
- [Using the API](#using-the-api)
- [Example questions](#example-questions)
- [Configuration reference](#configuration-reference)
- [Architecture details](#architecture-details)
- [Contributing](#contributing)

---

## How it works

```
Your question
      │
      ▼
OpenAI-compatible embedding model
      │  converts question to a vector
      ▼
FAISS vector store
      │  semantic search → top 5 most relevant document chunks
      ▼
LangChain RetrievalQA chain
      │  LLM reads chunks + question → generates grounded answer
      ▼
Answer + source citations
```

The key difference from asking an LLM directly: the answer is **grounded in the actual regulation text**. The LLM is used to synthesise and explain, not to recall from training data. Every answer includes references to the source document so you can verify it.

---

## Current status

| Feature | Status |
|---|---|
| `/rag/query` endpoint | Ready |
| FAISS vector store | Ready (needs documents ingested) |
| LangChain 0.2 retrieval chain | Ready |
| `/rag/ingest` endpoint | **Not yet implemented** — contributor opportunity |
| Pre-loaded regulatory documents | **Not yet added** — contributor opportunity |

The module returns `503 Service Unavailable` until documents are ingested. This is by design — it gives a clear, actionable error rather than hallucinated answers from an empty index.

---

## Ingesting regulatory documents

> The `/rag/ingest` endpoint is not yet implemented. The steps below describe how to ingest documents programmatically while that endpoint is being built.

### Step 1 — Obtain regulatory documents

Download the source PDFs and place them in `backend/data/regulatory_docs/`:

| Document | Source |
|---|---|
| EU AI Act (Regulation EU 2024/1689) | EUR-Lex |
| GDPR (Regulation EU 2016/679) | EUR-Lex |
| NIST AI RMF 1.0 | nist.gov |
| ISO/IEC 42001:2023 overview | iso.org (publicly available portions) |

> See the contributor issues for downloading and adding these documents.

### Step 2 — Build the FAISS index

```python
# From the backend/ directory with venv activated:
from app.modules.rag.vector_store import create_vector_store

create_vector_store([
    "data/regulatory_docs/eu_ai_act.pdf",
    "data/regulatory_docs/gdpr.pdf",
    "data/regulatory_docs/nist_ai_rmf.pdf",
])
# Index saved to: faiss_index/ (or FAISS_INDEX_PATH from .env)
```

This processes the PDFs into ~1000-character chunks with 200-character overlap, generates embeddings, and saves the FAISS index to disk. Depending on document size and provider, this may take 1–5 minutes.

### Step 3 — Verify

```bash
ls -la backend/faiss_index/
# index.faiss
# index.pkl
```

Once the index exists, `/rag/query` will return answers instead of 503.

---

## Querying the knowledge base

```bash
TOKEN=$(curl -s -X POST http://localhost:8000/api/v1/auth/login \
  -d "username=you@example.com&password=password" | jq -r .access_token)

curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the transparency obligations for chatbots under the EU AI Act?"}'
```

**Response:**
```json
{
  "answer": "Under Article 52(1) of the EU AI Act, providers of AI systems intended to interact with natural persons must ensure those systems disclose that the person is interacting with an AI, unless this is obvious from context. This obligation applies at the point of interaction and must be clear and comprehensible...",
  "sources": [
    "eu_ai_act.pdf",
    "eu_ai_act.pdf",
    "gdpr.pdf"
  ]
}
```

---

## Example questions

The RAG module is designed to answer practical compliance questions:

**Risk classification:**
- "Does my CV-screening tool qualify as high-risk under the EU AI Act?"
- "Is a credit scoring algorithm considered high-risk under Annex III?"
- "What AI systems are prohibited under Article 5?"

**Compliance obligations:**
- "What are the technical documentation requirements for high-risk AI systems?"
- "What is required under Article 9 — the risk management system obligation?"
- "What human oversight measures does Article 14 require?"

**GDPR intersection:**
- "How does the EU AI Act interact with GDPR for automated decision-making?"
- "What are the data governance requirements under both GDPR Article 22 and EU AI Act Article 10?"

**Multi-regulation:**
- "How does NIST AI RMF Map function compare to EU AI Act risk assessment requirements?"
- "What does ISO 42001 require that goes beyond the EU AI Act?"

---

## Using the API

### POST /rag/query

```bash
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What are the penalties for non-compliance with the EU AI Act?"
  }'
```

**Response `200`:**
```json
{
  "answer": "The EU AI Act establishes a tiered penalty regime...",
  "sources": ["eu_ai_act.pdf", "eu_ai_act.pdf"]
}
```

**Response `503`** (index not yet built):
```json
{
  "detail": "RAG module not ready: FAISS index not found at 'faiss_index'. Run POST /rag/ingest first."
}
```

### GET /rag/health

```bash
curl http://localhost:8000/api/v1/rag/health
# {"module": "rag_intelligence", "status": "available"}
```

---

## Configuration reference

| Variable | Default | Description |
|---|---|---|
| `LLM_API_KEY` | — | API key for embeddings + LLM (same provider as Guard) |
| `LLM_BASE_URL` | — | OpenAI-compatible base URL |
| `LLM_MODEL` | `gpt-4o-mini` | Model used for the QA chain |
| `FAISS_INDEX_PATH` | `faiss_index` | Directory where the FAISS index is persisted |
| `RAG_CHUNK_SIZE` | `1000` | Characters per document chunk |
| `RAG_CHUNK_OVERLAP` | `200` | Overlap between adjacent chunks |
| `S3_BUCKET_NAME` | — | S3 bucket for document storage (optional) |

**Choosing chunk size:** Smaller chunks (500–800) give more precise retrieval but less context per chunk. Larger chunks (1500–2000) give more context but may dilute relevance. 1000 is a good default for regulatory documents.

---

## Architecture details

### Document chunking

The `RecursiveCharacterTextSplitter` splits documents by trying paragraph breaks (`\n\n`), then line breaks (`\n`), then sentences, then characters — preserving semantic boundaries as much as possible.

```
PDF (e.g. 200 pages)
    │
    ▼
PyPDFLoader → list of Document objects (one per page)
    │
    ▼
RecursiveCharacterTextSplitter
  chunk_size=1000, chunk_overlap=200
    │
    ▼
~800–2000 chunks with metadata: {source, page}
```

### Embedding model

By default uses `text-embedding-ada-002` (OpenAI) or the equivalent from your configured provider. Embeddings are generated once during ingest and stored in the FAISS index — query embeddings are generated on each request.

With Ollama:
- Use `nomic-embed-text` for embeddings: `ollama pull nomic-embed-text`
- Note: Ollama embeddings and Ollama chat completions use different model names

### Retrieval

`k=5` — the five most semantically similar chunks are retrieved for each query. These chunks are injected into the LLM prompt as context using LangChain's `stuff` chain type (all chunks in a single prompt).

For very long regulatory documents, `map_reduce` or `refine` chain types may give better results — this is a contributor improvement opportunity.

---

## Contributing

The RAG module has several open contributor issues in the tracker:

**Beginner:**
- Download and add EU AI Act PDF to `backend/data/regulatory_docs/`
- Add GDPR, ISO 42001, and NIST AI RMF documents

**Intermediate:**
- Implement `POST /rag/ingest` endpoint (PDF upload → FAISS rebuild)
- Add RAG document management endpoints (list/delete ingested documents)
- Add source citation with article/paragraph reference to responses
- Add question history per user
- Integrate MLflow tracking
- Add streaming SSE responses

**Advanced:**
- Fine-tune an open-source regulatory model (Mistral/Llama) for better QA quality
- Add regulatory change detection feed (monitor EUR-Lex for amendments)
- Build compliance benchmarking API
