<div align="center">

# AegisAI

**Open-source AI Governance, Risk & Compliance (AI-GRC) Platform**

[![License: AGPL-3.0](https://img.shields.io/badge/License-AGPL%20v3-blue.svg)](https://www.gnu.org/licenses/agpl-3.0)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.109-009688?logo=fastapi)](https://fastapi.tiangolo.com)
[![React](https://img.shields.io/badge/React-18-61DAFB?logo=react)](https://react.dev)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

[Getting Started](docs/getting-started.md) · [Architecture](docs/architecture.md) · [API Reference](docs/api-reference.md) · [Guard Module](docs/guard-module.md) · [RAG Module](docs/rag-module.md) · [Report a Bug](https://github.com/SdSarthak/AegisAI/issues)

</div>

---

## What is AegisAI?

Every company shipping AI in Europe now faces legal obligations under the **EU AI Act** (in force April 2026). Most compliance tools cost thousands per month and are closed-source.

**AegisAI is the open-source alternative** — a full-stack platform that combines three things into one:

| Module | What it does |
|---|---|
| **Compliance Engine** | Register AI systems, classify EU AI Act risk (Minimal / Limited / High / Unacceptable), generate required documentation |
| **LLM Guard** | Real-time prompt injection detection using regex + DistilBERT/DeBERTa ML classifier — protect your LLM APIs |
| **RAG Intelligence** | Ask natural language questions about EU AI Act, GDPR, ISO 42001 — grounded answers from regulatory source docs |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, TypeScript, Vite, Tailwind CSS |
| Backend | Python 3.11, FastAPI, SQLAlchemy, PostgreSQL |
| ML (Guard) | PyTorch, HuggingFace Transformers (DeBERTa-v3), scikit-learn |
| RAG | LangChain, FAISS, OpenAI Embeddings |
| MLOps | MLflow, Prometheus metrics |
| Infra | Docker, Kubernetes (HPA configs included) |
| Auth | JWT, bcrypt |
| Payments | Stripe (optional) |

---

## Quick Start

### Option 1 — Docker (recommended)

```bash
git clone https://github.com/SdSarthak/AegisAI.git
cd AegisAI

cp backend/.env.example backend/.env
# Edit backend/.env — add your GEMINI_API_KEY and/or OPENAI_API_KEY

docker compose up -d
```

- Frontend: http://localhost:5173
- Backend API + Swagger: http://localhost:8000/docs

### Option 2 — Manual

```bash
# Backend
cd backend
python -m venv venv && source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env   # fill in values
uvicorn app.main:app --reload

# Frontend (new terminal)
cd frontend
npm install
npm run dev
```

---

## 📓 Colab Notebooks

If you want to train the machine learning models yourself, you can run our official Google Colab notebooks on a free T4 GPU:

- [![Open In Colab](https://colab.research.google.com/assets/colab-badge.svg)](https://colab.research.google.com/gist/amritanshu2611/7a533926b3df02d2ea0df5bd51641361/finetune_regulatory_model.ipynb) **Fine-tune Regulatory Q&A Model (Llama-3.2-3B QLoRA)**

---

## Project Structure

```
AegisAI/
├── backend/
│   ├── app/
│   │   ├── api/v1/          # REST endpoints (auth, ai_systems, guard, rag, ...)
│   │   ├── core/            # Config, DB, JWT security
│   │   ├── models/          # SQLAlchemy ORM models
│   │   ├── schemas/         # Pydantic request/response schemas
│   │   └── modules/
│   │       ├── guard/       # LLM Guard — regex + ML classifier + sanitizer
│   │       ├── rag/         # RAG — vector store, retrieval chain, MLflow
│   │       └── llm/         # LLM client (OpenAI-compatible)
│   ├── data/                # Training data for Guard classifier
│   └── tests/
├── frontend/                # React + TypeScript dashboard
├── infra/                   # Kubernetes deployment & HPA configs
├── notebooks/               # Jupyter — train Guard classifier on GPU (Colab-ready)
├── docs/                    # Architecture, API reference, module guides
└── docker-compose.yml
```

---

## Roadmap

- [x] EU AI Act risk classification engine
- [x] AI system registry + compliance dashboard
- [x] Compliance document generation (Technical Docs, Risk Assessment, Conformity Declaration)
- [x] LLM Guard — regex filter + ML intent classifier + sanitizer
- [x] RAG query endpoint (plug in your regulatory documents)
- [ ] Pre-loaded regulatory knowledge base (EU AI Act, GDPR, ISO 42001, NIST AI RMF)
- [ ] Audit log for all Guard scan decisions
- [ ] Stripe billing integration
- [ ] OAuth2 / SSO support
- [ ] Multi-regulation support (UK AI Bill, India DPDP)
- [ ] Analytics dashboard (compliance score over time)
- [ ] Slack / webhook notifications for compliance drift

> These open items are great places to contribute — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Contributing

We welcome contributions of all kinds — code, docs, tests, regulatory expertise.

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for the full guide.

**Not sure where to start?** Browse issues labelled:
- [`good first issue`](https://github.com/SdSarthak/AegisAI/labels/good%20first%20issue) — beginner-friendly
- [`help wanted`](https://github.com/SdSarthak/AegisAI/labels/help%20wanted) — intermediate
- [`high priority`](https://github.com/SdSarthak/AegisAI/labels/high%20priority) — advanced / impactful

---

## License

AegisAI is licensed under **AGPL-3.0-only**.

- Free for open-source and self-hosted use.
- If you run a modified version as a SaaS, you must release your source code.
- For commercial licensing, contact the author.

Copyright (C) 2024 **Sarthak Doshi** ([@SdSarthak](https://github.com/SdSarthak))

---

<div align="center">
  <sub>Built with care. If AegisAI helps you, give it a star.</sub>
</div>
