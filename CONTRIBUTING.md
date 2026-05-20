# Contributing to AegisAI

First off — thank you! AegisAI is built by the community and every contribution matters.

---

## Table of Contents

- [Code of Conduct](#code-of-conduct)
- [How to Contribute](#how-to-contribute)
- [Issue Labels — Find Your Level](#issue-labels--find-your-level)
- [Development Setup](#development-setup)
- [Pull Request Process](#pull-request-process)
- [Commit Style](#commit-style)
- [Project Structure Guide](#project-structure-guide)

---

## Code of Conduct

By participating, you agree to our [Code of Conduct](CODE_OF_CONDUCT.md). Be kind, constructive, and inclusive.

---

## How to Contribute

1. **Find an issue** — browse [Issues](https://github.com/SdSarthak/AegisAI/issues) or create one describing what you want to build.
2. **Comment** on the issue to claim it before starting — avoids duplicate work.
3. **Fork** the repo and create a branch: `git checkout -b feat/your-feature-name`
4. **Build** your change (see Development Setup below).
5. **Test** your code: `pytest backend/tests/`
6. **Open a PR** against `main` — use the PR template.

---

## Issue Labels — Find Your Level

### Beginner (`good first issue`)
No deep domain knowledge required. Great for getting familiar with the codebase.

Examples:
- Add missing docstrings to API endpoints
- Improve error messages (make them human-readable)
- Add type hints to functions that are missing them
- Fix a typo in documentation
- Add one more EU AI Act risk factor to the classification questionnaire
- Write a unit test for an existing function

### Intermediate (`help wanted`)
Requires understanding of the architecture and one of the three modules.

Examples:
- Add audit logging for Guard scan decisions (persist to DB)
- Add per-user rate limiting on `POST /guard/scan`
- Build a `GET /guard/stats` endpoint (block/allow/sanitize counts per user)
- Add a `POST /rag/ingest` endpoint to upload custom PDF documents
- Add more compliance document templates (Data Governance, Transparency Notice)
- Add pagination to list endpoints

### Advanced (`high priority`)
Architectural or ML work. Discuss in an issue before starting.

Examples:
- Pre-load the EU AI Act, GDPR, ISO 42001, NIST AI RMF as RAG source documents
- Integrate MLflow tracking into the RAG module
- Add OAuth2 / Google SSO support
- Build the analytics dashboard (compliance score over time charts)
- Add streaming responses (SSE) for RAG queries
- Fine-tune the Guard classifier on a larger prompt injection dataset
- Add Slack / webhook notification support for compliance drift alerts

---

## Development Setup

### Prerequisites
- Python 3.11+
- Node.js 18+
- Docker & Docker Compose
- PostgreSQL 15 (or just use Docker)

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env      # fill in your keys
uvicorn app.main:app --reload
```

API docs: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Running Tests

```bash
cd backend
pytest tests/ -v --cov=app
```

---

## Pull Request Process

1. Make sure tests pass locally before opening a PR.
2. Keep PRs focused — one feature or fix per PR.
3. Fill in the PR template completely.
4. Link the issue your PR closes: `Closes #123`
5. A maintainer will review within 48–72 hours.
6. Address review comments and push to the same branch — the PR updates automatically.

---

## Updating the Changelog

When submitting a PR, add a line to `CHANGELOG.md` under the `[Unreleased]` section using this format:

- **Added** `<new features>`
- **Fixed** `<bug fixes>`
- **Changed** `<changes to existing functionality>`
- **Removed** `<removed features>`

---

## Commit Style

We follow [Conventional Commits](https://www.conventionalcommits.org/):

```
feat: add audit log for guard scan decisions
fix: handle empty prompt in /guard/scan
docs: add RAG module usage guide
test: add unit tests for risk classifier
chore: bump fastapi to 0.110
```

---

## Project Structure Guide

| Path | What to touch |
|---|---|
| `backend/app/api/v1/` | Add or modify REST endpoints |
| `backend/app/modules/guard/` | LLM Guard ML logic |
| `backend/app/modules/rag/` | RAG / vector store logic |
| `backend/app/models/` | Database ORM models |
| `backend/app/schemas/` | Pydantic request/response shapes |
| `frontend/src/pages/` | React page components |
| `frontend/src/services/api.ts` | Frontend API calls |
| `docs/` | Documentation |

---

Questions? Open a [Discussion](https://github.com/SdSarthak/AegisAI/discussions) or ping in the issue thread.
