# RAG Intelligence Module

The RAG (Retrieval-Augmented Generation) module lets you ask natural language questions about AI regulations and receive grounded answers with source citations — rather than relying on an LLM's potentially outdated or hallucinated knowledge.

---

## Table of Contents

- [How it works](#how-it-works)
- [Current status](#current-status)
- [Ingesting regulatory documents](#ingesting-regulatory-documents)
- [Querying the knowledge base](#querying-the-knowledge-base)
- [Feedback and quality tracking](#feedback-and-quality-tracking)
- [Using the API](#using-the-api)
- [Example questions](#example-questions)
- [Configuration reference](#configuration-reference)
- [Architecture details](#architecture-details)
- [Evaluation dataset](#evaluation-dataset)
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
Answer + answer_id + source citations
      │
      ▼  (optional)
User submits vote via POST /rag/feedback
      │
      ▼
Low-quality chunks surfaced via GET /rag/low-quality-chunks
```

The key difference from asking an LLM directly: the answer is **grounded in the actual regulation text**. Every answer includes references to the source document so you can verify it.

---

## Current status

| Feature | Status |
|---|---|
| `/rag/query` endpoint | Ready |
| FAISS vector store | Ready (needs documents ingested) |
| LangChain 0.2 retrieval chain | Ready |
| `/rag/feedback` — thumbs up/down on answers | Ready |
| `/rag/low-quality-chunks` — admin quality view | Ready |
| EU AI Act PDF in `regulatory_docs/` | PR #176 open |
| `/rag/ingest` endpoint | Contributor opportunity |
| Pre-loaded GDPR, ISO 42001, NIST AI RMF | Contributor opportunity |

The module returns `503 Service Unavailable` until documents are ingested — a clear actionable error rather than hallucinated answers from an empty index.

---

## Ingesting regulatory documents

> The `/rag/ingest` endpoint is not yet implemented. The steps below describe how to ingest documents programmatically while that endpoint is being built.

### Step 1 — Obtain regulatory documents

Download the source PDFs and place them in `backend/data/regulatory_docs/`:

| Document | Source |
|---|---|
| EU AI Act (Regulation EU 2024/1689) | EUR-Lex (PR #176 is adding this) |
| GDPR (Regulation EU 2016/679) | EUR-Lex |
| ISO/IEC 42001:2023 | iso.org (publicly available portions) |
| NIST AI RMF 1.0 | nist.gov |

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

This processes PDFs into ~1000-character chunks with 200-character overlap, generates embeddings, and saves the FAISS index to disk. Takes 1–5 minutes depending on document size and provider.

### Step 3 — Verify

```bash
ls -la backend/faiss_index/
# index.faiss
# index.pkl
```

Once the index exists, `/rag/query` returns answers instead of 503.

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
  "answer": "Under Article 52(1) of the EU AI Act, providers of AI systems intended to interact with natural persons must ensure those systems disclose that the person is interacting with an AI...",
  "answer_id": "a7f3c291-4b2e-...",
  "sources": [
    "eu_ai_act.pdf",
    "eu_ai_act.pdf",
    "gdpr.pdf"
  ]
}
```

Save the `answer_id` — you'll need it to submit feedback.

---

## Feedback and quality tracking

After receiving an answer, submit a vote to help improve the knowledge base.

### Submit feedback

```bash
curl -X POST http://localhost:8000/api/v1/rag/feedback \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "answer_id": "a7f3c291-4b2e-...",
    "vote": "down"
  }'
```

**Vote values:** `"up"` | `"down"`

### View low-quality chunks (admin/scale tier)

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/rag/low-quality-chunks?threshold=0.3"
```

**Response:**
```json
[
  {
    "chunk": "eu_ai_act.pdf::page_42",
    "thumbs_down": 7,
    "total": 9,
    "ratio": 0.78
  }
]
```

**Knowledge base maintenance workflow:**
1. Users query → server stores `answer_id` + contributing chunk sources
2. Users submit `"down"` votes on poor answers
3. Admin queries `low-quality-chunks` to identify chunks to re-ingest or remove
4. Re-ingest corrected documents → rebuild FAISS index

---

## Example questions

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

See [regulations.md](regulations.md) for a full comparison of EU AI Act, UK AI Bill, and India DPDP.

---

## Using the API

### POST /rag/query

```bash
curl -X POST http://localhost:8000/api/v1/rag/query \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"question": "What are the penalties for non-compliance with the EU AI Act?"}'
```

**Response `200`:**
```json
{
  "answer": "The EU AI Act establishes a tiered penalty regime...",
  "answer_id": "a7f3c291-4b2e-...",
  "sources": ["eu_ai_act.pdf", "eu_ai_act.pdf"]
}
```

**Response `503`** (index not yet built):
```json
{
  "detail": "RAG module not ready: FAISS index not found at 'faiss_index'. Run POST /rag/ingest first."
}
```

### POST /rag/feedback

```bash
curl -X POST http://localhost:8000/api/v1/rag/feedback \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"answer_id": "a7f3c291-...", "vote": "up"}'
```

### GET /rag/low-quality-chunks

```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8000/api/v1/rag/low-quality-chunks?threshold=0.3"
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

**Choosing chunk size:** Smaller chunks (500–800) give more precise retrieval. Larger chunks (1500–2000) give more context per chunk. 1000 is a good default for regulatory documents.

---

## Architecture details

### Document chunking

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

The `RecursiveCharacterTextSplitter` preserves semantic boundaries by trying paragraph breaks, then line breaks, then sentences, then characters.

### Embedding model

By default uses `text-embedding-ada-002` (OpenAI) or the equivalent from your configured provider. Embeddings are generated once during ingest and stored in the FAISS index. Query embeddings are generated on each request.

With Ollama: `ollama pull nomic-embed-text` then set your embedding model in `.env`.

### Retrieval

`k=5` — the five most semantically similar chunks are retrieved per query. Chunks are injected into the LLM prompt using LangChain's `stuff` chain type.

---

## Evaluation dataset

`backend/data/regulatory_qa.csv` contains 75 question-answer pairs covering EU AI Act, GDPR, and ISO 42001. Use this dataset to evaluate retrieval quality after ingesting regulatory documents:

```bash
# Example: measure answer accuracy against the QA dataset
python scripts/evaluate_rag.py --dataset data/regulatory_qa.csv
```

(Evaluation script is a contributor opportunity — see issue tracker.)

---

## Contributing

**Good first issue:**
- Download and add the EU AI Act PDF to `backend/data/regulatory_docs/` (see PR #176)
- Add GDPR, ISO 42001, and NIST AI RMF documents

**Intermediate:**
- Implement `POST /rag/ingest` endpoint (PDF upload → FAISS rebuild)
- Add source citation with article/paragraph reference to responses
- Add question history per user
- Add streaming SSE responses
- Write RAG evaluation script using `regulatory_qa.csv`
- Integrate MLflow tracking

**Advanced:**
- Fine-tune an open-source regulatory model (Mistral/Llama) for better QA quality
- Add regulatory change detection feed (monitor EUR-Lex for amendments)
- Build compliance benchmarking API using the QA dataset
