"""
AegisAI — Open-source AI Governance, Risk & Compliance Platform
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.core.config import settings
from app.core.database import engine, Base
from app.api.v1 import api_router
import app.models  # ensure all ORM models are imported so tables are created

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="AegisAI",
    description=(
        "Open-source AI Governance, Risk & Compliance platform. "
        "Helps organisations comply with the EU AI Act, guard LLM systems "
        "against prompt injection, and query regulatory knowledge via RAG."
    ),
    version="0.1.0",
    docs_url="/docs",
    redoc_url="/redoc",
    license_info={
        "name": "AGPL-3.0",
        "url": "https://www.gnu.org/licenses/agpl-3.0.html",
    },
    contact={
        "name": "Sarthak Doshi",
        "url": "https://github.com/SdSarthak/AegisAI",
    },
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.get("/", tags=["Health"])
def root():
    return {
        "project": "AegisAI",
        "version": "0.1.0",
        "docs": "/docs",
        "github": "https://github.com/SdSarthak/AegisAI",
        "modules": ["compliance", "guard", "rag"],
    }


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
