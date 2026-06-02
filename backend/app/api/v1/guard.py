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
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
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
    prompt: str = Field(..., min_length=1, max_length=settings.GUARD_MAX_PROMPT_LENGTH)


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

        for i, prompt in enumerate(self.prompts):
            if not prompt or len(prompt) > settings.GUARD_MAX_PROMPT_LENGTH:
                raise ValueError(
                    f"Prompt at index {i} must be between 1 and "
                    f"{settings.GUARD_MAX_PROMPT_LENGTH} characters."
                )


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

    limited, retry_after = guard_scan_rate_limiter.check_and_consume(
        key=f"guard:scan:{current_user.id}",
        limit=settings.GUARD_RATE_LIMIT_REQUESTS,
        window_seconds=settings.GUARD_RATE_LIMIT_WINDOW_SECONDS,
        fail_closed=True,
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

        client_ip = http_request.client.host if http_request.client else None
        background_tasks.add_task(
            log_scan,
            current_user.id,
            request.prompt,
            result,
            client_ip,
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


@router.get("/stats", response_model=GuardStatsResponse)
def get_guard_stats(
    window: str = Query("7d", pattern="^(24h|7d|30d|all)$"),
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    target_user_id = user_id if user_id is not None else current_user.id
    is_admin = getattr(current_user, "role", None) == "admin"

    if target_user_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to query stats for another user.",
        )

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


@router.get("/config", tags=["LLM Guard"])
def get_guard_config(current_user: User = Depends(get_current_user)):

    default_config = {
        "sanitization_level": "medium",
        "malicious_threshold": 0.8,
        "suspicious_threshold": 0.5,
    }

    return user_guard_configs.get(current_user.id, default_config)


@router.patch("/config", tags=["LLM Guard"])
def update_guard_config(
    config: GuardConfigRequest,
    current_user: User = Depends(get_current_user),
):

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


@router.post("/scan/batch", response_model=BulkScanResponse)
def bulk_scan_prompts(
    request: BulkScanRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    try:
        request.validate_prompts()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    batch_size = len(request.prompts)
    client_ip = http_request.client.host if http_request.client else None

    limited, retry_after = guard_scan_rate_limiter.check_and_consume(
        key=f"guard:scan:{current_user.id}",
        limit=settings.GUARD_RATE_LIMIT_REQUESTS,
        window_seconds=settings.GUARD_RATE_LIMIT_WINDOW_SECONDS,
        cost=batch_size,
        fail_closed=True,
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
            log = _build_guard_scan_log(current_user.id, prompt, result, ip_address=client_ip)

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


@router.get("/info", tags=["LLM Guard"])
def guard_info():

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


@router.get("/stats", response_model=GuardStatsResponse)
def get_guard_stats(
    window: str = Query("7d", pattern="^(24h|7d|30d|all)$"),
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    target_user_id = user_id if user_id is not None else current_user.id
    is_admin = getattr(current_user, "role", None) == "admin"

    if target_user_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to query stats for another user.",
        )

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


@router.get("/config", tags=["LLM Guard"])
def get_guard_config(current_user: User = Depends(get_current_user)):

    default_config = {
        "sanitization_level": "medium",
        "malicious_threshold": 0.8,
        "suspicious_threshold": 0.5,
    }

    return user_guard_configs.get(current_user.id, default_config)


@router.patch("/config", tags=["LLM Guard"])
def update_guard_config(
    config: GuardConfigRequest,
    current_user: User = Depends(get_current_user),
):

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


@router.post("/scan/batch", response_model=BulkScanResponse)
def bulk_scan_prompts(
    request: BulkScanRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    try:
        request.validate_prompts()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    batch_size = len(request.prompts)
    client_ip = http_request.client.host if http_request.client else None

    limited, retry_after = guard_scan_rate_limiter.check_and_consume(
        key=f"guard:scan:{current_user.id}",
        limit=settings.GUARD_RATE_LIMIT_REQUESTS,
        window_seconds=settings.GUARD_RATE_LIMIT_WINDOW_SECONDS,
        cost=batch_size,
        fail_closed=True,
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
            log = _build_guard_scan_log(current_user.id, prompt, result, ip_address=client_ip)

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


@router.get("/info", tags=["LLM Guard"])
def guard_info():

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


@router.get("/stats", response_model=GuardStatsResponse)
def get_guard_stats(
    window: str = Query("7d", pattern="^(24h|7d|30d|all)$"),
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):

    target_user_id = user_id if user_id is not None else current_user.id
    is_admin = getattr(current_user, "role", None) == "admin"

    if target_user_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to query stats for another user.",
        )

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


@router.get("/config", tags=["LLM Guard"])
def get_guard_config(current_user: User = Depends(get_current_user)):

    default_config = {
        "sanitization_level": "medium",
        "malicious_threshold": 0.8,
        "suspicious_threshold": 0.5,
    }

    return user_guard_configs.get(current_user.id, default_config)


@router.patch("/config", tags=["LLM Guard"])
def update_guard_config(
    config: GuardConfigRequest,
    current_user: User = Depends(get_current_user),
):

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


@router.post("/scan/batch", response_model=BulkScanResponse)
def bulk_scan_prompts(
    request: BulkScanRequest,
    http_request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    try:
        request.validate_prompts()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    batch_size = len(request.prompts)
    client_ip = http_request.client.host if http_request.client else None

    limited, retry_after = guard_scan_rate_limiter.check_and_consume(
        key=f"guard:scan:{current_user.id}",
        limit=settings.GUARD_RATE_LIMIT_REQUESTS,
        window_seconds=settings.GUARD_RATE_LIMIT_WINDOW_SECONDS,
        cost=batch_size,
        fail_closed=True,
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
            log = _build_guard_scan_log(current_user.id, prompt, result, ip_address=client_ip)

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