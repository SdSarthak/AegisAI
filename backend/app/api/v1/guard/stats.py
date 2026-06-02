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


@router.get("/history", response_model=PaginatedResponse[GuardScanLogResponse])
def get_guard_history(
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current user's Guard scan history, newest first.

    Args:
        skip: Number of items to skip for pagination.
        limit: Maximum number of scan logs to include per page.
        db: Database session used to query scan history.
        current_user: Authenticated user whose history is requested.

    Returns:
        PaginatedResponse containing the user's scan history.
    """
    try:
        base_query = db.query(GuardScanLog).filter(
            GuardScanLog.user_id == current_user.id,
        )

        total = base_query.count()
        logs = (
            base_query.order_by(GuardScanLog.scanned_at.desc())  # FIX: use indexed scanned_at
            .offset(skip)
            .limit(limit)
            .all()
        )

        return PaginatedResponse(items=logs, total=total, skip=skip, limit=limit)
    except Exception as e:
        logger.exception("Failed to get guard history")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching scan history."
        )


@router.get("/stats", response_model=GuardStatsResponse)
def get_guard_stats(
    window: str = Query("7d", pattern="^(24h|7d|30d|all)$"),
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return Guard scan statistics for a time window and user.

    Args:
        window: Time window to aggregate over (24h, 7d, 30d, or all).
        user_id: Optional user ID to query; defaults to the current user.
        db: Database session used to aggregate scan statistics.
        current_user: Authenticated user requesting the statistics.

    Returns:
        GuardStatsResponse containing decision, detection, and trend statistics.

    Raises:
        HTTPException: If the caller is not allowed to query another user's stats.
    """
    target_user_id = user_id if user_id is not None else current_user.id
    is_admin = getattr(current_user, "role", None) == "admin"

    if target_user_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to query stats for another user.",
        )

    try:
        now = datetime.utcnow()
        if window == "24h":
            start_date = now - timedelta(hours=24)
        elif window == "7d":
            start_date = now - timedelta(days=7)
        elif window == "30d":
            start_date = now - timedelta(days=30)
        else:
            start_date = None

        base_filters = [GuardScanLog.user_id == target_user_id]
        if start_date:
            base_filters.append(GuardScanLog.scanned_at >= start_date)

        base_query = db.query(GuardScanLog).filter(*base_filters)
        total_scans = base_query.count()

        by_decision = {
            "allow": {"count": 0, "pct": 0.0},
            "sanitize": {"count": 0, "pct": 0.0},
            "block": {"count": 0, "pct": 0.0},
        }

        decision_counts = (
            db.query(GuardScanLog.decision, func.count(GuardScanLog.id))
            .filter(*base_filters)
            .group_by(GuardScanLog.decision)
            .all()
        )

        for decision, count in decision_counts:
            if decision in by_decision:
                by_decision[decision]["count"] = count
                by_decision[decision]["pct"] = (
                    round((count / total_scans) * 100, 1) if total_scans else 0.0
                )

        by_detection_type = {
            "none": {"count": 0, "pct": 0.0},
            "regex": {"count": 0, "pct": 0.0},
            "ml": {"count": 0, "pct": 0.0},
            "combined": {"count": 0, "pct": 0.0},
        }

        detection_counts = (
            db.query(GuardScanLog.detection_type, func.count(GuardScanLog.id))
            .filter(*base_filters)
            .group_by(GuardScanLog.detection_type)
            .all()
        )

        for detection_type, count in detection_counts:
            if detection_type in by_detection_type:
                by_detection_type[detection_type]["count"] = count
                by_detection_type[detection_type]["pct"] = (
                    round((count / total_scans) * 100, 1) if total_scans else 0.0
                )

        all_patterns: list[str] = []
        logs_with_patterns = (
            db.query(GuardScanLog.matched_patterns)
            .filter(*base_filters)
            .all()
        )

        for (matched_patterns,) in logs_with_patterns:
            if isinstance(matched_patterns, list):
                all_patterns.extend(matched_patterns)

        top_matched_patterns = [
            {"pattern": pattern, "count": count}
            for pattern, count in Counter(all_patterns).most_common(10)
        ]

        daily_rows = (
            db.query(
                func.date(GuardScanLog.scanned_at).label("date"),
                GuardScanLog.decision,
                func.count(GuardScanLog.id),
            )
            .filter(*base_filters)
            .group_by("date", GuardScanLog.decision)
            .order_by("date")
            .all()
        )

        daily_buckets: dict[str, int] = {}

        for day, decision, count in daily_rows:
            date_key = str(day)
            if date_key not in daily_buckets:
                daily_buckets[date_key] = {
                    "date": date_key,
                    "count": 0,
                    "allow": 0,
                    "sanitize": 0,
                    "block": 0,
                }

            if decision in {"allow", "sanitize", "block"}:
                daily_buckets[date_key][decision] = count
                daily_buckets[date_key]["count"] += count

        scans_per_day = list(daily_buckets.values())

        return {
            "window": window,
            "total_scans": total_scans,
            "by_decision": by_decision,
            "by_detection_type": by_detection_type,
            "top_matched_patterns": top_matched_patterns,
            "scans_per_day": scans_per_day,
        }
    except Exception as e:
        logger.exception("Failed to get guard stats")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while computing guard stats."
        )


