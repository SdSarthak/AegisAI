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


@router.get("/config", tags=["LLM Guard"])
def get_guard_config(current_user: User = Depends(get_current_user)):
    """Return the current user's Guard configuration.

    Args:
        current_user: Authenticated user whose Guard config is requested.

    Returns:
        The user's saved Guard configuration, or the default config.
    """
    try:
        default_config = {
            "sanitization_level": "medium",
            "malicious_threshold": 0.8,
            "suspicious_threshold": 0.5,
        }

        return user_guard_configs.get(current_user.id, default_config)
    except Exception as e:
        logger.exception("Failed to get guard config")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching guard config."
        )


@router.patch("/config", tags=["LLM Guard"])
def update_guard_config(
    config: GuardConfigRequest,
    current_user: User = Depends(get_current_user),
):
    """Update the current user's Guard configuration.

    Args:
        config: Sanitization level and threshold values to persist.
        current_user: Authenticated user whose Guard config is being updated.

    Returns:
        A confirmation payload containing the saved configuration.

    Raises:
        HTTPException: If any configuration value is out of range.
    """
    try:
        if config.sanitization_level not in VALID_SANITIZATION_LEVELS:
            raise HTTPException(
                status_code=400,
                detail="Invalid sanitization level",
            )

        if not (0.0 <= config.malicious_threshold <= 1.0):
            raise HTTPException(
                status_code=400,
                detail="malicious_threshold must be between 0 and 1",
            )

        if not (0.0 <= config.suspicious_threshold <= 1.0):
            raise HTTPException(
                status_code=400,
                detail="suspicious_threshold must be between 0 and 1",
            )

        user_guard_configs[current_user.id] = {
            "sanitization_level": config.sanitization_level,
            "malicious_threshold": config.malicious_threshold,
            "suspicious_threshold": config.suspicious_threshold,
        }

        return {
            "message": "Guard configuration updated successfully",
            "config": user_guard_configs[current_user.id],
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.exception("Failed to update guard config")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating guard config."
        )


