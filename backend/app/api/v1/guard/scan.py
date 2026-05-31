"""
LLM Guard API — exposes prompt injection scanning as a REST endpoint.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

TODO for contributors (medium difficulty):
  - Add per-user rate limiting on POST /guard/scan
  - Persist scan results to the database for audit logs (Completed)
  - Add a GET /guard/stats endpoint returning block/allow/sanitize counts (Completed)
"""

import hashlib
import logging
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional, TypedDict

from app.api.v1.webhooks import deliver_webhook
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.notifications import create_notification
from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user
from app.core.rate_limit import guard_scan_rate_limiter
from app.models.guard_scan_log import GuardScanLog
from app.models.notification import NotificationType
from app.models.user import User
from app.schemas.guard_scan_log import GuardScanLogResponse
from app.schemas.guard_stats import GuardStatsResponse
from app.schemas.guard_explain import (
    ExplainRequest as ExplainRequestModel,
    ExplainResponse,
)
from app.schemas.pagination import PaginatedResponse
from app.modules.guard import guard_config

router = APIRouter()
logger = logging.getLogger(__name__)

# Backward-compatible test aliases for the shared rate limiter.
_scan_attempts_by_user = guard_scan_rate_limiter._local_attempts_by_key
_RATE_LIMIT_REQUESTS = settings.GUARD_RATE_LIMIT_REQUESTS


class ScanRequest(BaseModel):
    prompt: str


class ScanResponse(BaseModel):
    decision: str
    confidence: float
    reasoning: str
    sanitized_prompt: str | None = None
    matched_patterns: list[str] = []


class GuardConfigRequest(BaseModel):
    sanitization_level: str
    malicious_threshold: float
    suspicious_threshold: float


class BulkScanRequest(BaseModel):
    prompts: list[str]

    def validate_prompts(self) -> None:
        if not self.prompts:
            raise ValueError("At least one prompt is required per batch request.")

        if len(self.prompts) > 50:
            raise ValueError("Maximum 50 prompts allowed per batch request.")


class BulkScanResponse(BaseModel):
    results: list[ScanResponse]
    total: int
    processed: int


VALID_SANITIZATION_LEVELS = {"low", "medium", "high"}


class UserGuardConfig(TypedDict):
    sanitization_level: str
    malicious_threshold: float
    suspicious_threshold: float


# Temporary in-memory config store
user_guard_configs: dict[int, UserGuardConfig] = {}


def _infer_detection_type(regex_flag: bool, intent: str) -> str:
    """Infer whether regex, ML, both, or neither triggered the scan decision."""
    if not regex_flag and intent == "benign":
        return "none"
    if regex_flag and intent == "benign":
        return "regex"
    if not regex_flag and intent in {"suspicious", "malicious"}:
        return "ml"
    return "combined"


def _build_guard_scan_log(user_id: int, prompt: str, result: dict) -> GuardScanLog:
    """Build a GuardScanLog row without storing raw prompt text."""
    metadata = result.get("metadata", {})
    regex_analysis = metadata.get("regex_analysis", {})
    intent_analysis = metadata.get("intent_analysis", {})
    decision_reasoning = metadata.get("decision_reasoning", {})

    regex_flag = regex_analysis.get("flag", False)
    intent = intent_analysis.get("intent", "benign")
    detection_type = _infer_detection_type(regex_flag, intent)

    return GuardScanLog(
        user_id=user_id,
        prompt_hash=hashlib.sha256(prompt.encode()).hexdigest(),
        decision=result.get("decision", "allow"),
        confidence=decision_reasoning.get("confidence", 0.0),
        matched_patterns=regex_analysis.get("matched_patterns", []),
        detection_type=detection_type,
        regex_flag=regex_flag,
        regex_score=regex_analysis.get("risk_score", 0.0),
        intent=intent,
        ml_confidence=intent_analysis.get("confidence", 0.0),
        combined_score=decision_reasoning.get("confidence", 0.0),
        prompt_length=len(prompt),
        scanned_at=datetime.utcnow(),
    )


def log_scan(user_id: int, prompt: str, result: dict) -> None:
    """Log scan details and create block notification without storing raw prompt."""
    db = SessionLocal()

    try:
        log = _build_guard_scan_log(user_id, prompt, result)

        db.add(log)
        db.commit()
        db.refresh(log)

        if log.decision == "block":
            create_notification(
                db=db,
                user_id=user_id,
                notification_type=NotificationType.GUARD_BLOCK.value,
                title="Prompt blocked by LLM Guard",
                message="A prompt was blocked because it matched high-risk guard rules.",
                resource_type="guard_scan",
                resource_id=log.id,
            )
            db.commit()

    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


@router.post("/scan", response_model=ScanResponse)
def scan_prompt(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),              # added this for fixing nameerror crash
):
    """Scan a prompt for injection risks.

    Args:
        request: Prompt text and scan options submitted by the client.
        background_tasks: FastAPI background task runner used for scan logging.
        current_user: Authenticated user submitting the prompt.

    Returns:
        ScanResponse describing the guard decision and any sanitization details.

    Raises:
        HTTPException: If scan processing fails or the request is rate limited.
    """
    limited, retry_after = guard_scan_rate_limiter.check_and_consume(
        key=f"guard:scan:{current_user.id}",
        limit=settings.GUARD_RATE_LIMIT_REQUESTS,
        window_seconds=settings.GUARD_RATE_LIMIT_WINDOW_SECONDS,
    )

    if limited:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": (
                    f"Rate limit exceeded: {settings.GUARD_RATE_LIMIT_REQUESTS} "
                    f"requests per {settings.GUARD_RATE_LIMIT_WINDOW_SECONDS} seconds per user. Please try again later."
                ),
            },
            headers={"Retry-After": str(retry_after)},
        )

    try:
        from app.modules.guard.llm_guard import LLMGuard
        from app.modules.guard.sanitizer import SanitizationLevel

        level_map = {
            "low": SanitizationLevel.LOW,
            "medium": SanitizationLevel.MEDIUM,
            "high": SanitizationLevel.HIGH,
        }
        san_level = level_map.get(
            settings.GUARD_SANITIZATION_LEVEL,
            SanitizationLevel.MEDIUM,
        )

        guard = LLMGuard(sanitization_level=san_level)
        result = guard.guard(request.prompt)

        background_tasks.add_task(
            log_scan,
            current_user.id,
            request.prompt,
            result,
        )

        return ScanResponse(
            decision=result["decision"],
            confidence=result["metadata"]["decision_reasoning"]["confidence"],
            reasoning=result["metadata"]["decision_reasoning"]["reasoning"],
            sanitized_prompt=result.get("sanitized_prompt"),
            matched_patterns=result["metadata"]["regex_analysis"].get(
                "matched_patterns",
                [],
            ),
        )

        if result["decision"] == "block":
            try:
                deliver_webhook(
                    db=db,
                    user_id=current_user.id,
                    event="guard_block",
                    payload={
                        "decision": "block",
                        "confidence": response.confidence,
                        "matched_patterns": response.matched_patterns,
                        "prompt_hash": hashlib.sha256(
                            request.prompt.encode()
                        ).hexdigest(),
                    },
                    background_tasks=background_tasks,
                )
            except Exception:
                logger.exception("Failed to trigger guard_block webhook delivery")

        return response

    except Exception as e:
        logger.exception("Guard scan failed")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing the Guard scan.",
        )


# ---------------------------------------------------------------------------
# POST /guard/explain - SHAP/LIME explainability (issue #77)
# ---------------------------------------------------------------------------


class _ExplainRateLimitConfig:
    """Explanations are 50–100x more expensive than a scan — limit them
    aggressively. Tunable via env if needed; defaults are conservative."""

    LIMIT = 10
    WINDOW_SECONDS = 60
    TIMEOUT_SECONDS = 15.0


@router.post("/scan/batch", response_model=BulkScanResponse)
def bulk_scan_prompts(
    request: BulkScanRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Scan a batch of prompts for injection risks.

    Args:
        request: Prompt list payload to scan in one batch.
        current_user: Authenticated user submitting the batch.
        db: Database session used to persist batch scan results.

    Returns:
        BulkScanResponse containing scan results, totals, and processed count.

    Raises:
        HTTPException: If the batch exceeds limits or validation fails.
    """
    try:
        request.validate_prompts()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    batch_size = len(request.prompts)

    limited, retry_after = guard_scan_rate_limiter.check_and_consume(
        key=f"guard:scan:{current_user.id}",
        limit=settings.GUARD_RATE_LIMIT_REQUESTS,
        window_seconds=settings.GUARD_RATE_LIMIT_WINDOW_SECONDS,
        cost=batch_size,
    )

    if limited:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": (
                    f"Rate limit exceeded: {settings.GUARD_RATE_LIMIT_REQUESTS} "
                    f"requests per {settings.GUARD_RATE_LIMIT_WINDOW_SECONDS} seconds per user. Please try again later."
                ),
            },
            headers={"Retry-After": str(retry_after)},
        )

    try:
        from app.modules.guard.llm_guard import LLMGuard
        from app.modules.guard.sanitizer import SanitizationLevel

        level_map = {
            "low": SanitizationLevel.LOW,
            "medium": SanitizationLevel.MEDIUM,
            "high": SanitizationLevel.HIGH,
        }
        san_level = level_map.get(
            settings.GUARD_SANITIZATION_LEVEL,
            SanitizationLevel.MEDIUM,
        )

        guard = LLMGuard(sanitization_level=san_level)
        results: list[ScanResponse] = []

        for prompt in request.prompts:
            result = guard.guard(prompt)
            log = _build_guard_scan_log(current_user.id, prompt, result)

            db.add(log)
            db.flush()

            if log.decision == "block":
                create_notification(
                    db=db,
                    user_id=current_user.id,
                    notification_type=NotificationType.GUARD_BLOCK.value,
                    title="Prompt blocked by LLM Guard",
                    message="A prompt was blocked because it matched high-risk guard rules.",
                    resource_type="guard_scan",
                    resource_id=log.id,
                )

            results.append(
                ScanResponse(
                    decision=result["decision"],
                    confidence=result["metadata"]["decision_reasoning"]["confidence"],
                    reasoning=result["metadata"]["decision_reasoning"]["reasoning"],
                    sanitized_prompt=result.get("sanitized_prompt"),
                    matched_patterns=result["metadata"]["regex_analysis"].get(
                        "matched_patterns",
                        [],
                    ),
                )
            )

        db.commit()

        return BulkScanResponse(
            results=results,
            total=len(request.prompts),
            processed=len(results),
        )

    except Exception as e:
        db.rollback()
        logger.exception("Bulk guard scan failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing the batch Guard scan."
        )


