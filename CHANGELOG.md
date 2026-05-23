# Changelog

All notable changes to AegisAI are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/).

---

## [Unreleased]

### Added
- NotificationBell component now fetches real unread notifications from API with 60-second polling
- Notifications page wired to real API backend with mark-all-read and delete functionality
- Error states with retry buttons for notification loading failures
- Loading states with spinner animations for better UX
- Exponential backoff retry logic for resilient API calls

### Fixed
- Notification API response handling now correctly extracts items from paginated response
- Notification type mapping corrected to display proper colors for backend enum values
- Response field mismatch resolved (notification_type instead of type)

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
