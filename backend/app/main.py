"""
AegisAI — Open-source AI Governance, Risk & Compliance Platform
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Dict, Any

from fastapi import FastAPI, Request
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import settings
from app.core.context import get_request_id
from app.core.database import engine, Base
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware
from app.middleware.csrf import CSRFMiddleware
from app.core.telemetry import setup_telemetry
from app.api.v1 import api_router, badge
from app.plugins.regulation_loader import init_registry
from app.tasks.scheduler import scheduler, snapshot_compliance_scores, send_reassessment_reminders
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

    # Initialize background scheduler for periodic jobs
    scheduler.add_job(
        snapshot_compliance_scores,
        "cron",
        hour=2,
        minute=0,
        id="compliance_snapshot",
        replace_existing=True,
    )
    scheduler.add_job(
        send_reassessment_reminders,
        "cron",
        hour=8,
        minute=0,
        id="reassessment_reminder",
        replace_existing=True,
    )
    scheduler.start()
    logger.info("Compliance scheduler started")

    yield  # Control is passed to FastAPI and the application runs

    logger.info("Shutting down AegisAI backend...")
    scheduler.shutdown()
    logger.info("Compliance scheduler shut down")

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
app.add_middleware(CSRFMiddleware)

# Added last => outermost: every request (incl. CORS preflight and error
# responses) is assigned a request id and access-logged in JSON.
app.add_middleware(RequestContextMiddleware)
app.add_middleware(SessionMiddleware, secret_key=settings.SECRET_KEY)

# -------------------------------------------------------------------
# Error Handlers — include request_id in every error response body
# -------------------------------------------------------------------

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException) -> JSONResponse:
    headers = getattr(exc, "headers", None)
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "request_id": get_request_id(),
        },
        headers=headers,
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(
        status_code=422,
        content={
            "detail": jsonable_encoder(exc.errors()),
            "request_id": get_request_id(),
        },
    )

@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception", extra={"error": str(exc)})
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": get_request_id(),
        },
    )

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


@app.get("/ready", tags=["Health"])
def readiness_check() -> Dict[str, Any]:
    """
    Readiness probe — confirms the application can serve traffic.
    """
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
