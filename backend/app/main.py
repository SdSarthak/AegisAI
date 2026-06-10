"""FastAPI application bootstrap for the AegisAI backend.

This module wires together logging, telemetry, middleware, routes, and the
application lifespan hooks that prepare the database and regulation registry
at startup.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

import app.models  # ensure all ORM models are imported so tables are created
from app.api.v1 import api_router, badge
from app.core.config import settings
from app.core.database import Base, engine
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.core.telemetry import setup_telemetry
from app.plugins.regulation_loader import init_registry

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
    """Handle FastAPI startup and shutdown events."""
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
# Observability (OTel + Prometheus instrumentation)
# -------------------------------------------------------------------
setup_telemetry(app)
logger.info("Telemetry instrumentation initialised.")

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
    """Return a lightweight health check response with DB status."""
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


@app.get("/ready", tags=["Health"])
def readiness_check() -> Dict[str, Any]:
    """Return a readiness probe that confirms the database is reachable."""
    db_ready = False
    try:
        with engine.connect() as connection:
            connection.execute(text("SELECT 1"))
        db_ready = True
    except SQLAlchemyError:
        logger.exception("Readiness check — database not reachable")

    ready = db_ready
    return {
        "ready": ready,
        "database": db_ready,
        "version": app.version,
        "service": "AegisAI Backend",
    }
