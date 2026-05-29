# Changelog

All notable changes to AegisAI are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

## [Unreleased]

### Added
- **Pre-commit hooks** — Added `.pre-commit-config.yaml` with repository hygiene hooks (trailing-whitespace, end-of-file-fixer, check-merge-conflict, check-yaml, check-json) and a local ESLint hook wrapping the existing frontend lint command.
- **LLM Guard Prompt Normalization** — Preprocessor layer (`normalizer.py`) to prevent Unicode, zero-width, and homoglyph bypasses:
  - Strips invisible format characters in Unicode `Cf` category (e.g. zero-width space, non-joiner, joiner)
  - Normalizes stylized font variations using NFKC compatibility normalization
  - Resolves Cyrillic and Greek homoglyphs to standard Latin equivalents via static mapping
  - Retains both `normalized_prompt` and `user_prompt` in orchestrator response
- Unit and integration tests for bypass payloads (`test_normalizer.py` and `test_guard.py`)

### Fixed
- **Documents API** — Validate `ai_system_id` ownership before creating documents so users cannot link documents to another user's AI system.
- **RAG FAISS index rebuilds** — Stage, validate, and swap rebuilt indexes under thread/process locking so concurrent ingests cannot write directly into the shared live index.

---

## [Unreleased]

### Added
- **Compliance Engine** — Added Education & Vocational Training (Annex III point 3) risk factor to EU AI Act classification.
- LLM Guard console with copy-to-clipboard exports for scan response payloads and raw audit metrics.

---

## [0.1.0] — 2026-04-05

### Added
- **Compliance Engine** — EU AI Act risk classification (Minimal / Limited / High / Unacceptable)
- AI system registry with CRUD endpoints
- Compliance document generation (Technical Documentation, Risk Assessment, Conformity Declaration)
- JWT authentication (register, login, `/me`)
- **LLM Guard module** — 4-layer prompt injection defence:
  - Regex heuristic filter
  - DeBERTa-v3 intent classifier (benign / suspicious / malicious)
  - Decision engine (allow / sanitize / block)
  - Prompt sanitizer (LOW / MEDIUM / HIGH levels)
- `POST /api/v1/guard/scan` endpoint
- **RAG Intelligence module** — FAISS vector store + LangChain 0.2 retrieval chain
- `POST /api/v1/rag/query` endpoint
- Provider-agnostic LLM client (OpenAI-compatible: works with Ollama, Groq, Together AI, vLLM …)
- React 18 + TypeScript frontend (Dashboard, AI Systems, Classification, Documents)
- Docker Compose setup
- Kubernetes deployment & HPA configs
- Colab-ready notebook for fine-tuning the Guard classifier

### Known Limitations (good first contributions!)
- RAG knowledge base is empty by default — needs regulatory documents ingested
- No audit log for Guard decisions yet
- Stripe billing wired up but not activated
- Frontend pages for Guard and RAG not yet built
