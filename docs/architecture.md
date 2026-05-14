# Architecture Overview

---

## Table of Contents

- [High-level diagram](#high-level-diagram)
- [Module breakdown](#module-breakdown)
- [Data flows](#data-flows)
- [Database schema](#database-schema)
- [Authentication flow](#authentication-flow)
- [Directory structure](#directory-structure)
- [Key design decisions](#key-design-decisions)

---

## High-level diagram

```
┌──────────────────────────────────────────────────────────────────────┐
│                         React 18 Frontend                            │
│                                                                      │
│  Dashboard · AI Systems · Classification · Documents · Analytics     │
│  Notifications · Onboarding · [RAG Chat — in progress]              │
│                                                                      │
│  Zustand auth store · TanStack Query · Tailwind CSS                  │
│  react-hot-toast · react-hook-form + zod                             │
└───────────────────────────────┬──────────────────────────────────────┘
                                │  REST/JSON  (axios + Bearer JWT)
┌───────────────────────────────▼──────────────────────────────────────┐
│                     FastAPI Backend  /api/v1/                        │
│                                                                      │
│  ┌─────────────────┐  ┌────────────────┐  ┌──────────────────────┐  │
│  │ Compliance      │  │ LLM Guard      │  │ RAG Intelligence     │  │
│  │ Engine          │  │ Module         │  │ Module               │  │
│  │                 │  │                │  │                      │  │
│  │ /ai-systems     │  │ /guard/scan    │  │ /rag/query           │  │
│  │   + import CSV  │  │   (rate-       │  │ /rag/feedback        │  │
│  │   + search/     │  │    limited)    │  │ /rag/low-quality-    │  │
│  │     filter      │  │ /guard/health  │  │   chunks             │  │
│  │ /classification │  │                │  │ /rag/health          │  │
│  │ /documents      │  │ 1. Regex       │  │                      │  │
│  │   + PDF export  │  │ 2. DeBERTa-v3  │  │ FAISS index          │  │
│  │ /analytics      │  │ 3. Decision    │  │ LangChain chain      │  │
│  │ /badge/{id}     │  │ 4. Sanitizer   │  │ Feedback model       │  │
│  │ /notifications  │  │                │  │ MLflow (stub)        │  │
│  │ /webhooks       │  │ guard-sdk/     │  │                      │  │
│  │ /users/me PATCH │  │ (standalone)   │  │                      │  │
│  └────────┬────────┘  └───────┬────────┘  └──────────┬───────────┘  │
│           │                   │                       │              │
│  ┌────────▼───────────────────▼───────────────────────▼───────────┐  │
│  │         Core: JWT Auth · SQLAlchemy ORM · Pydantic Config      │  │
│  └────────────────────────────┬───────────────────────────────────┘  │
└───────────────────────────────┼──────────────────────────────────────┘
                                │
             ┌──────────────────▼──────────────────┐
             │           PostgreSQL 15              │
             │  users · ai_systems · documents      │
             │  rag_feedback                        │
             │  audit_log (migration pending)       │
             │  notifications (migration pending)   │
             └─────────────────────────────────────┘
```

---

## Module breakdown

### Module 1 — Compliance Engine

Handles EU AI Act compliance tracking from system registration through document generation.

| File | Responsibility |
|---|---|
| `api/v1/ai_systems.py` | CRUD + bulk CSV import + search/risk/compliance filter |
| `api/v1/classification.py` | Risk classification (Article 5, 6, 52 + Annex III) |
| `api/v1/documents.py` | Document generation from templates + PDF export |
| `api/v1/analytics.py` | Compliance metrics aggregation |
| `api/v1/badge.py` | SVG compliance badge endpoint |
| `models/ai_system.py` | `AISystem` ORM; `compliance_score` is nullable Float |
| `models/document.py` | `Document` ORM model |
| `modules/badge/badge_generator.py` | SVG badge renderer |

**Risk levels:**

| Level | EU AI Act basis | Examples |
|---|---|---|
| Unacceptable | Article 5 (prohibited) | Social scoring, real-time biometric ID in public spaces |
| High | Article 6 + Annex III | CV screening, credit scoring, medical devices, law enforcement |
| Limited | Article 52 (transparency) | Chatbots, deepfake generators, emotion recognition |
| Minimal | — | Spam filters, inventory management, video games |

---

### Module 2 — LLM Guard

A four-layer defence pipeline that inspects every prompt before it reaches an LLM.

| File | Responsibility |
|---|---|
| `modules/guard/regex_rules.py` | Layer 1: fast regex heuristics, ~0ms |
| `modules/guard/intent_classifier.py` | Layer 2: DeBERTa-v3-small transformer, CPU ~200ms |
| `modules/guard/decision_engine.py` | Layer 3: combines regex + ML scores into a decision |
| `modules/guard/sanitizer.py` | Layer 4: removes meta-instructions from SANITIZE-level prompts |
| `modules/guard/llm_guard.py` | Orchestrator — runs all 4 layers |
| `modules/guard/guard_config.py` | Paths, thresholds, intent class mappings |
| `modules/guard/train.py` | Training script for fine-tuning the classifier |
| `api/v1/guard.py` | REST endpoint with per-user rate limiting |
| `guard-sdk/` | Standalone package (`pip install aegisai-guard`) |
| `scripts/scan_prompts.py` | CLI to scan `.prompts/` files against the Guard API |
| `.github/workflows/guard-scan.yml` | CI action — scans `.prompts/` on every PR |
| `notebooks/train_guard_classifier.ipynb` | Colab fine-tuning notebook |

**Regex categories:**

| Category | Examples | Severity |
|---|---|---|
| Instruction override | "ignore all previous instructions" | High (0.9) |
| Role hijacking | "you are now DAN", "act as an evil AI" | High (0.8) |
| Prompt disclosure | "repeat your system prompt" | Medium (0.6) |
| Policy bypass | "pretend you have no restrictions" | Medium (0.7) |
| Dangerous code | `exec()`, `eval()`, `os.system()` | Medium/High |
| Suspicious keywords | "jailbreak", "override", "bypass" | Low (0.3) |

**Decision thresholds (configurable via `.env`):**

| Signal | Weight |
|---|---|
| Regex score | 0.4 |
| ML classifier score | 0.6 |
| Suspicious threshold | 0.5 → SANITIZE |
| Malicious threshold | 0.8 → BLOCK |

---

### Module 3 — RAG Intelligence

A retrieval-augmented generation pipeline with answer quality feedback.

| File | Responsibility |
|---|---|
| `modules/rag/document_loader.py` | Loads PDFs, splits into chunks |
| `modules/rag/vector_store.py` | Builds and persists FAISS index |
| `modules/rag/retrieval_chain.py` | LangChain RetrievalQA chain (k=5 chunks) |
| `modules/rag/ml_flow.py` | MLflow query tracking stub |
| `api/v1/rag.py` | Query, feedback, and low-quality-chunk endpoints |
| `models/rag_feedback.py` | Vote storage per answer |
| `data/regulatory_qa.csv` | 75-row QA evaluation dataset |

---

## Data flows

### Guard scan pipeline

```
POST /api/v1/guard/scan
        │
        ▼
  JWT auth + per-user rate limit check  (429 if exceeded)
        │
        ▼
  LLMGuard.guard(prompt)
        │
        ├─► Layer 1: RegexFilter.check(prompt)
        │       flag, score (0–1), matched_patterns
        │
        ├─► Layer 2: IntentClassifier.classify(prompt)
        │       intent (benign/suspicious/malicious), confidence
        │
        ├─► Layer 3: DecisionEngine.decide(regex, intent)
        │       decision (ALLOW/SANITIZE/BLOCK), reasoning
        │
        └─► Layer 4 (if SANITIZE): PromptSanitizer.sanitize(prompt)
                Returns cleaned_prompt
                    │
                    ▼
              LLMClient.call(cleaned_prompt)

BLOCK    → return safe error (no LLM call)
ALLOW    → LLMClient.call(prompt)
SANITIZE → LLMClient.call(sanitized_prompt)
```

### Risk classification flow

```
POST /api/v1/classification/classify/{system_id}
        │
        ▼
  Receive RiskClassificationRequest (~12 boolean fields)
        │
        ▼
  Check Article 5 prohibited uses
        │
        ▼
  Check Annex III high-risk categories
        │
        ▼
  Check Article 52 transparency obligations
        │
        ▼
  Return RiskClassificationResponse
  + save RiskAssessment to DB
  + update AISystem.risk_level
```

### RAG query + feedback flow

```
POST /api/v1/rag/query
        │
        ▼
  load_vector_store()  (503 if index not built)
        │
        ▼
  FAISS semantic search (k=5)
        │
        ▼
  LangChain RetrievalQA.run(question, chunks)
        │
        ▼
  Return {answer, answer_id, sources}

          ▼  (later, optional)
POST /api/v1/rag/feedback {"answer_id": ..., "vote": "down"}
          │
          ▼
  Store in rag_feedback table

GET /api/v1/rag/low-quality-chunks?threshold=0.3
  → aggregate by chunk source, return high thumbs-down ratio chunks
```

---

## Database schema

```
users
  id (PK)
  email (unique)
  hashed_password
  full_name, company_name
  subscription_tier          ENUM(free, starter, growth, scale)
  stripe_customer_id, stripe_subscription_id
  is_active
  created_at / updated_at

ai_systems
  id (PK)
  owner_id (FK → users)
  name, description, version, use_case, sector
  risk_level                 ENUM(minimal, limited, high, unacceptable)
  compliance_status          ENUM(not_started, in_progress, compliant, non_compliant)
  compliance_score           Float (nullable)
  questionnaire_responses    JSON
  created_at / updated_at

documents
  id (PK)
  owner_id (FK → users)
  ai_system_id (FK → ai_systems)
  title
  document_type              ENUM(technical_documentation, risk_assessment,
                                  conformity_declaration, ...)
  status                     ENUM(draft, generated, approved, archived)
  content                    Text (Markdown)
  file_path                  nullable (PDF path)
  created_at / updated_at

rag_feedback
  id (PK)
  answer_id                  String (UUID from /rag/query response)
  chunk_source               String (source document + page ref)
  vote                       ENUM(up, down)
  user_id (FK → users)
  created_at

-- Pending migrations:
audit_log                    (PR #160 open)
notifications                (PR #175 open)
webhooks                     (scaffold — no migration yet)
compliance_snapshots         (scaffold — no migration yet)
```

---

## Authentication flow

```
POST /api/v1/auth/register  →  hash password (bcrypt)  →  store user  →  201
POST /api/v1/auth/login     →  verify password  →  issue JWT (30min)  →  200
GET  /api/v1/auth/me        →  decode JWT  →  load user  →  200
PATCH /api/v1/users/me      →  decode JWT  →  update fields  →  200

All protected routes:
  Authorization: Bearer <token>
      │
      ▼
  get_current_user() dependency
      │
      ▼
  python-jose JWT decode  →  load User from DB
      ├── Invalid/expired  →  401
      └── Valid            →  inject User into route handler
```

**JWT payload:**
```json
{"sub": "user@example.com", "exp": 1234567890}
```

---

## Directory structure

```
AegisAI/
├── backend/
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── __init__.py          ← router registration
│   │   │   ├── auth.py              ← register, login, /me
│   │   │   ├── ai_systems.py        ← CRUD + import CSV + search/filter
│   │   │   ├── classification.py    ← EU AI Act risk classification
│   │   │   ├── documents.py         ← doc generation + PDF export
│   │   │   ├── guard.py             ← prompt scan + per-user rate limiting
│   │   │   ├── rag.py               ← query + feedback + low-quality chunks
│   │   │   ├── analytics.py         ← compliance metrics aggregation
│   │   │   ├── badge.py             ← SVG badge endpoint
│   │   │   ├── notifications.py     ← in-app notifications (scaffold)
│   │   │   └── webhooks.py          ← webhook listeners (scaffold)
│   │   ├── core/
│   │   │   ├── config.py            ← pydantic-settings (reads .env)
│   │   │   ├── database.py          ← SQLAlchemy engine + session
│   │   │   └── security.py          ← JWT, bcrypt, get_current_user
│   │   ├── models/
│   │   │   ├── user.py
│   │   │   ├── ai_system.py         ← includes compliance_score (nullable Float)
│   │   │   ├── document.py
│   │   │   ├── rag_feedback.py      ← vote storage per answer
│   │   │   ├── audit_log.py         ← scaffold (migration pending PR #160)
│   │   │   ├── compliance_snapshot.py ← scaffold
│   │   │   ├── notification.py      ← scaffold (migration pending PR #175)
│   │   │   └── webhook.py           ← scaffold
│   │   ├── schemas/
│   │   │   ├── user.py              ← UserCreate, UserResponse, UserUpdate, Token
│   │   │   ├── ai_system.py         ← RiskClassificationRequest/Response
│   │   │   ├── document.py
│   │   │   └── analytics.py
│   │   ├── modules/
│   │   │   ├── guard/               ← 4-layer pipeline + train script
│   │   │   ├── rag/                 ← FAISS + LangChain + feedback aggregation
│   │   │   ├── llm/llm_client.py    ← OpenAI-compatible LLM wrapper
│   │   │   └── badge/badge_generator.py  ← SVG renderer
│   │   ├── tasks/scheduler.py       ← APScheduler scaffold
│   │   └── main.py                  ← FastAPI app, CORS, router mount
│   ├── data/
│   │   ├── regulatory_qa.csv        ← 75-row QA evaluation dataset
│   │   └── regulatory_docs/         ← Add regulatory PDFs here
│   ├── tests/
│   │   ├── conftest.py              ← Shared fixtures (TestClient, DB session)
│   │   ├── test_guard.py, test_guard_config.py, test_sanitizer.py
│   │   ├── test_llm_client.py
│   │   ├── test_retrieval_chain.py
│   │   ├── test_badge.py
│   │   ├── test_bulk_import.py
│   │   ├── test_auth_me.py
│   │   └── integration/
│   │       ├── test_pdf_export.py
│   │       ├── test_rag_feedback.py
│   │       └── test_rate_limiting.py
│   ├── .env.example
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── pages/
│       │   ├── Dashboard.tsx, AISystems.tsx, Classification.tsx
│       │   ├── Documents.tsx, Analytics.tsx, Notifications.tsx
│       │   ├── Onboarding.tsx, Login.tsx, Register.tsx
│       ├── components/
│       │   ├── Layout.tsx, ComplianceChecklist.tsx, DocumentEditor.tsx
│       │   ├── NotificationBell.tsx, ThemeToggle.tsx
│       ├── services/api.ts          ← Axios + all API call wrappers
│       ├── stores/authStore.ts      ← Zustand auth state
│       └── utils/toast.ts           ← react-hot-toast helpers
├── guard-sdk/                       ← Standalone PyPI package (v0.1.0)
├── mcp/server.py                    ← MCP server scaffold
├── infra/
│   ├── deployment.yaml              ← Kubernetes Deployment + Service + PVC
│   └── hpa.yaml                     ← HorizontalPodAutoscaler
├── notebooks/train_guard_classifier.ipynb
├── scripts/scan_prompts.py          ← CLI Guard scan for .prompts/ files
├── postman/AegisAI.postman_collection.json
├── docs/
│   ├── getting-started.md
│   ├── architecture.md
│   ├── api-reference.md
│   ├── guard-module.md
│   ├── rag-module.md
│   └── regulations.md
├── .github/
│   ├── workflows/ci.yml             ← backend tests + frontend lint/build
│   └── workflows/guard-scan.yml     ← prompt injection CI scan (implemented)
└── docker-compose.yml
```

---

## Key design decisions

### 1. OpenAI-compatible LLM client
Both Guard and RAG use a single `LLMClient` speaking the OpenAI chat-completions API. Provider is swappable with a single `.env` change — OpenAI, Ollama, Groq, Together AI, vLLM all work without code changes.

### 2. Four-layer Guard pipeline
Each layer has a distinct cost/coverage tradeoff. The pipeline is fail-safe: if the DeBERTa model fails to load, it falls back to the pre-trained base rather than disabling the Guard entirely.

### 3. Per-user rate limiting on Guard scan
Prevents abuse without authentication bypass. The limit is configurable via environment variables.

### 4. FAISS local vector store
Chosen over managed solutions (Pinecone, Weaviate) to keep the stack fully self-contained. The index is persisted to disk and loaded at startup.

### 5. compliance_score as nullable Float
Allows AI systems to exist without a score until a rollup job or user action computes it — avoids misleading zero-default values.

### 6. RAG feedback model
The `rag_feedback` table records per-answer votes, enabling the `low-quality-chunks` endpoint to surface chunks needing re-ingestion. This closes the loop between user feedback and knowledge base quality.

### 7. AGPL-3.0 licence
Ensures companies running AegisAI as a hosted SaaS must release modifications, preventing closed-source forks while keeping it free for self-hosted deployments.

### 8. Module isolation
Guard has no database dependency and ships as a standalone `guard-sdk` package. RAG requires only a FAISS index and an LLM API key.
