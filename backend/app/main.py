"""
AegisAI — Open-source AI Governance, Risk & Compliance Platform
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app.core.config import settings
from app.core.database import engine, Base
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.api.v1 import api_router, badge
from app.schemas.rag import RAG_QUESTION_MAX_LENGTH
from app.plugins.regulation_loader import init_registry
import app.models  # ensure all ORM models are imported so tables are created

# -------------------------------------------------------------------
# Logging Setup
# -------------------------------------------------------------------
# Structured single-line JSON logs to stdout (parseable by Datadog / Loki /
# CloudWatch). Honour DEBUG from settings; everything else stays at INFO.
configure_logging(level="DEBUG" if settings.DEBUG else "INFO")
logger = logging.getLogger("aegisai.main")

# -------------------------------------------------------------------
# Lifespan Handler
# -------------------------------------------------------------------
@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Handles startup and shutdown events for the FastAPI application.
    """
    logger.info("Starting AegisAI backend...")

    try:
        # Initialize database tables during application startup
        Base.metadata.create_all(bind=engine)
        logger.info("Database tables initialized.")
    except Exception:
        logger.exception("Failed to initialize database tables")
        raise

    # Initialize regulation ruleset registry (stored on app.state for route access)
    builtin_dir = Path(__file__).resolve().parent.parent / "regulations"
    custom_dir = builtin_dir / "custom"
    app.state.registry = init_registry(builtin_dir, custom_dir)
    logger.info("Regulation registry initialized.")

    yield  # Control is passed to FastAPI and the application runs

    logger.info("Shutting down AegisAI backend...")
    # Place any teardown logic here (e.g., closing thread pools, background tasks)

# -------------------------------------------------------------------
# FastAPI Application Initialization
# -------------------------------------------------------------------
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
    lifespan=lifespan,
)


@app.exception_handler(RequestValidationError)
async def request_validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return a friendly message for oversized RAG questions."""
    is_rag_query = request.url.path == f"{settings.API_V1_PREFIX}/rag/query"
    question_too_long = any(
        error.get("type") == "string_too_long"
        and list(error.get("loc", ())) == ["body", "question"]
        for error in exc.errors()
    )

    if is_rag_query and question_too_long:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={
                "detail": (
                    f"Question is too long. Please keep it under "
                    f"{RAG_QUESTION_MAX_LENGTH} characters."
                )
            },
        )

    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={"detail": jsonable_encoder(exc.errors())},
    )

# -------------------------------------------------------------------
# Middleware
# -------------------------------------------------------------------
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Added last => outermost: every request (incl. CORS preflight and error
# responses) is assigned a request id and access-logged in JSON.
app.add_middleware(RequestContextMiddleware)

# -------------------------------------------------------------------
# Routing
# -------------------------------------------------------------------
app.include_router(api_router, prefix=settings.API_V1_PREFIX)
app.include_router(badge.router, prefix="/badge")

# -------------------------------------------------------------------
# Root & Health Endpoints
# -------------------------------------------------------------------
@app.get("/", tags=["Health"])
def root() -> Dict[str, Any]:
    return {
        "project": "AegisAI",
        "version": app.version,
        "docs": app.docs_url,
        "github": "https://github.com/SdSarthak/AegisAI",
        "modules": ["compliance", "guard", "rag"],
    }

@app.get("/health", tags=["Health"])
def health_check() -> Dict[str, Any]:
    """
    Validates application health and verifies database connectivity.
    """
    db_status = "connected"
    overall_status = "healthy"

    try:
        # Perform a lightweight ping to the database to ensure connection is alive
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
    except SQLAlchemyError:
        logger.exception("Database health check failed")
        db_status = "disconnected"
        overall_status = "degraded"

    return {
        "status": overall_status,
        "database": db_status,
        "version": app.version,
        "service": "AegisAI Backend"
    }
