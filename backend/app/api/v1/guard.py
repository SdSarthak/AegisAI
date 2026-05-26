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
from collections import Counter, defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Optional
import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.api.v1.notifications import create_notification
from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.core.security import get_current_user
from app.models.guard_scan_log import GuardScanLog
from app.models.notification import NotificationType
from app.models.user import User
from app.schemas.guard_scan_log import GuardScanLogResponse
from app.schemas.guard_stats import GuardStatsResponse
from app.schemas.pagination import PaginatedResponse
from app.modules.guard import guard_config

router = APIRouter()
logger = logging.getLogger(__name__)

_RATE_LIMIT_REQUESTS = 60
_RATE_LIMIT_WINDOW_SECONDS = 60
_scan_attempts_by_user: dict[int, deque[datetime]] = defaultdict(deque)
_rate_limit_lock = Lock()


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
        if len(self.prompts) > 50:
            raise ValueError("Maximum 50 prompts allowed per batch request.")


class BulkScanResponse(BaseModel):
    results: list[ScanResponse]
    total: int
    processed: int


VALID_SANITIZATION_LEVELS = {"low", "medium", "high"}
user_guard_configs: dict[int, dict[str, float | str]] = {}


def _check_rate_limit(user_id: int) -> tuple[bool, int]:
    """Check whether a user has exceeded the per-user rate limit.

    Uses a sliding-window algorithm (60 requests / 60 seconds) with a
    thread-safe deque per user.

    Args:
        user_id: Primary-key of the user to check.

    Returns:
        A ``(is_limited, retry_after)`` tuple.  ``is_limited`` is ``True``
        when the window is full; ``retry_after`` is the number of seconds
        the caller should wait before retrying.
    """
    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=_RATE_LIMIT_WINDOW_SECONDS)

    with _rate_limit_lock:
        attempts = _scan_attempts_by_user[user_id]

        while attempts and attempts[0] <= window_start:
            attempts.popleft()

        if len(attempts) >= _RATE_LIMIT_REQUESTS:
            retry_after = max(
                1,
                int(
                    (
                        _RATE_LIMIT_WINDOW_SECONDS
                        - (now - attempts[0]).total_seconds()
                    )
                    + 0.999
                ),
            )
            return True, retry_after

        attempts.append(now)
        return False, 0


def _infer_detection_type(regex_flag: bool, intent: str) -> str:
    """Infer the detection source that triggered the scan decision.

    Args:
        regex_flag: ``True`` if the regex analyser flagged the prompt.
        intent: Intent label from the ML classifier (``benign``,
            ``suspicious``, or ``malicious``).

    Returns:
        One of ``"none"``, ``"regex"``, ``"ml"``, or ``"combined"``.
    """
    if not regex_flag and intent == "benign":
        return "none"
    if regex_flag and intent == "benign":
        return "regex"
    if not regex_flag and intent in {"suspicious", "malicious"}:
        return "ml"
    return "combined"


def _build_guard_scan_log(user_id: int, prompt: str, result: dict) -> GuardScanLog:
    """Build a ``GuardScanLog`` ORM instance from a scan result.

    The raw prompt text is **not** stored — only its SHA-256 hash —
    to avoid persisting potentially sensitive or adversarial content.

    Args:
        user_id: ID of the user who initiated the scan.
        prompt: The original prompt string (hashed, not stored).
        result: Raw result dict returned by ``LLMGuard.guard()``.

    Returns:
        GuardScanLog: A populated (but uncommitted) ORM instance.
    """
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
    """Persist scan results and fire a block notification (background task).

    Called via ``BackgroundTasks`` so the HTTP response is not delayed.
    Opens its own ``SessionLocal`` to avoid sharing the request session.

    Args:
        user_id: ID of the user who performed the scan.
        prompt: The original prompt (hashed before storage).
        result: Raw result dict from ``LLMGuard.guard()``.
    """
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
):
    """Scan a single prompt for injection risks.

    Applies regex-based and ML-based analysis, then returns a decision
    of ``allow``, ``sanitize``, or ``block``.  The scan result is
    persisted asynchronously via a background task.

    Args:
        request: Body containing the ``prompt`` string to scan.
        background_tasks: FastAPI background-task scheduler (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        ScanResponse: Decision, confidence score, reasoning, and any
            matched regex patterns.

    Raises:
        HTTPException(429): If the user exceeds 60 requests per minute.
        HTTPException(500): If the guard engine encounters an internal error.
    """
    limited, retry_after = _check_rate_limit(current_user.id)

    if limited:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": "Rate limit exceeded: 60 requests per minute per user. Please try again later.",
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
            sanitized_prompt=None,
            matched_patterns=result["metadata"]["regex_analysis"].get(
                "matched_patterns",
                [],
            ),
        )

    except Exception as e:
        logger.exception("Guard scan failed")

        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while processing the Guard scan."
        )


@router.get("/health", tags=["LLM Guard"])
def guard_health():
    """Liveness probe for the Guard module.

    No authentication required.  Returns a simple status dict.

    Returns:
        dict: ``{"module": "llm_guard", "status": "available"}``.
    """
    return {"module": "llm_guard", "status": "available"}


@router.get("/info", tags=["LLM Guard"])
def guard_info():
    """Return diagnostic information about the Guard module.

    Reports the compute device (``cpu`` or ``cuda``), loaded model name,
    and active sanitisation level.  No authentication required.

    Returns:
        dict: Keys ``module``, ``status``, ``device``, ``model_name``,
            ``sanitization_level``.
    """

    try:
        import torch
        device = "cuda" if torch.cuda.is_available() else "cpu"
    except ImportError:
        device = "cpu"

    from pathlib import Path

    model_path = Path(guard_config.get_trained_model_path()).name

    return {
        "module": "llm_guard",
        "status": "available",
        "device": device,
        "model_name": model_path or "pretrained-fallback",
        "sanitization_level": guard_config.SANITIZATION_LEVEL,
    }

VALID_DECISIONS = {"allow", "sanitize", "block"}
VALID_INTENTS = {"benign", "suspicious", "malicious"}


def build_history_filters(
    current_user_id: int,
    decision: Optional[str],
    intent: Optional[str],
    start_date: Optional[datetime],
    end_date: Optional[datetime],
):
    filters = [GuardScanLog.user_id == current_user_id]

    # -----------------------
    # decision filter
    # -----------------------
    if decision:
        decision = decision.strip().lower()

        if decision not in VALID_DECISIONS:
            raise HTTPException(
                status_code=400,
                detail="Invalid decision filter",
            )

        filters.append(GuardScanLog.decision == decision)

    # -----------------------
    # intent filter
    # -----------------------
    if intent:
        intent = intent.strip().lower()

        if intent not in VALID_INTENTS:
            raise HTTPException(
                status_code=400,
                detail="Invalid intent filter",
            )

        filters.append(GuardScanLog.intent == intent)

    # -----------------------
    # date filters
    # -----------------------
    if start_date:
        filters.append(GuardScanLog.scanned_at >= start_date)

    if end_date:
        filters.append(GuardScanLog.scanned_at <= end_date)

    return filters

@router.get("/history", response_model=PaginatedResponse[GuardScanLogResponse])
def get_guard_history(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),

    decision: Optional[str] = Query(None),
    intent: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current user's Guard scan history, newest first.

    Supports optional filtering by decision, intent, and date range.

    Args:
        page: 1-indexed page number.
        limit: Items per page (1–100, default 20).
        decision: Optional filter — ``allow``, ``sanitize``, or ``block``.
        intent: Optional filter — ``benign``, ``suspicious``, or ``malicious``.
        start_date: Optional inclusive lower bound (ISO 8601).
        end_date: Optional inclusive upper bound (ISO 8601).
        db: SQLAlchemy session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        PaginatedResponse[GuardScanLogResponse]: Paginated scan logs.

    Raises:
        HTTPException(400): If ``start_date > end_date``, or if an invalid
            decision/intent filter value is supplied.
    """

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=400,
            detail="start_date cannot be after end_date",
        )

    filters = build_history_filters(
        current_user.id,
        decision,
        intent,
        start_date,
        end_date
    )

    query = db.query(GuardScanLog).filter(*filters)

    total = query.count()

    logs = (
        query.order_by(GuardScanLog.scanned_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return PaginatedResponse(
        items=logs,
        total=total,
        page=page,
        limit=limit,
    )


@router.get("/stats", response_model=GuardStatsResponse)
def get_guard_stats(
    window: str = Query("7d", pattern="^(24h|7d|30d|all)$"),
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return aggregate Guard scan statistics.

    Computes totals, decision breakdown, detection-type breakdown,
    top matched regex patterns, and daily scan counts for the
    requested time window.

    Args:
        window: Time window — ``24h``, ``7d``, ``30d``, or ``all``.
        user_id: Optional target user ID (admin-only; defaults to self).
        db: SQLAlchemy session (injected).
        current_user: Authenticated user (injected via JWT).

    Returns:
        GuardStatsResponse: Aggregated statistics dict.

    Raises:
        HTTPException(403): If a non-admin user tries to query another
            user's statistics.
    """
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

    daily_buckets: dict[str, dict[str, int | str]] = {}

    for day, decision, count in daily_rows:
        date_key = str(day)
        if date_key not in daily_buckets:
            daily_buckets[date_key] = {
                "date": date_key,
                "allow": 0,
                "sanitize": 0,
                "block": 0,
            }

        if decision in {"allow", "sanitize", "block"}:
            daily_buckets[date_key][decision] = count

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
    """Retrieve the in-memory guard configuration for the current user.

    Returns stored overrides if present, otherwise the default config:
    ``{"sanitization_level": "medium", "malicious_threshold": 0.8,
    "suspicious_threshold": 0.5}``.

    Args:
        current_user: Authenticated user (injected via JWT).

    Returns:
        dict: Keys ``sanitization_level`` (str), ``malicious_threshold``
            (float), and ``suspicious_threshold`` (float).
    """
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
    """Update the in-memory guard configuration for the current user.

    Validates that the sanitisation level is one of ``low``, ``medium``,
    or ``high`` and that both threshold values fall within ``[0.0, 1.0]``.

    Args:
        config: Request body with ``sanitization_level``,
            ``malicious_threshold``, and ``suspicious_threshold``.
        current_user: Authenticated user (injected via JWT).

    Returns:
        dict: Confirmation message and the updated config.

    Raises:
        HTTPException(400): If the sanitisation level is invalid or a
            threshold is outside the ``[0, 1]`` range.
    """
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Scan a batch of prompts (max 50) for injection risks.

    Each prompt counts as one rate-limit unit.  Rate-limit availability is
    checked **upfront** for the entire batch; individual prompts are then
    scanned sequentially.  All ``GuardScanLog`` rows are committed in a
    single transaction.

    Args:
        request: Body containing a ``prompts`` list (≤ 50 strings).
        current_user: Authenticated user (injected via JWT).
        db: SQLAlchemy session (injected).

    Returns:
        BulkScanResponse: Per-prompt results with ``total`` and
            ``processed`` counts.

    Raises:
        HTTPException(400): If more than 50 prompts are supplied.
        HTTPException(429): If the batch would exceed the rate limit.
        HTTPException(500): If the guard engine encounters an internal error.
    """
    try:
        request.validate_prompts()
    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )

    now = datetime.now(timezone.utc)
    window_start = now - timedelta(seconds=_RATE_LIMIT_WINDOW_SECONDS)
    batch_size = len(request.prompts)

    with _rate_limit_lock:
        attempts = _scan_attempts_by_user[current_user.id]

        while attempts and attempts[0] <= window_start:
            attempts.popleft()

        if len(attempts) + batch_size > _RATE_LIMIT_REQUESTS:
            retry_after = (
                max(
                    1,
                    int(
                        (
                            _RATE_LIMIT_WINDOW_SECONDS
                            - (now - attempts[0]).total_seconds()
                        )
                        + 0.999
                    ),
                )
                if attempts
                else _RATE_LIMIT_WINDOW_SECONDS
            )

            return JSONResponse(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                content={"detail": "Rate limit exceeded. Please try again later."},
                headers={"Retry-After": str(retry_after)},
            )

        for _ in range(batch_size):
            attempts.append(now)

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
                    sanitized_prompt=None,
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
    
