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
from typing import Optional, TypedDict

from app.api.v1.webhooks import deliver_webhook
import logging
import base64
from collections import Counter
from datetime import datetime, timedelta, timezone
from typing import Optional, TypedDict

from app.api.v1.webhooks import deliver_webhook

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
from sqlalchemy import func, and_, or_
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
from app.schemas.pagination import CursorPaginatedResponse

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
    """Infer whether regex, ML, both, or neither triggered the scan decision."""
    if not regex_flag and intent == "benign":
        return "none"
    if regex_flag and intent == "benign":
        return "regex"
    if not regex_flag and intent in {"suspicious", "malicious"}:
        return "ml"
    return "combined"


def _build_guard_scan_log(user_id: int, prompt: str, result: dict, ip_address: str | None = None) -> GuardScanLog:
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
        ip_address=ip_address,
    )


def log_scan(user_id: int, prompt: str, result: dict, ip_address: str | None = None) -> None:
    """Log scan details and create block notification without storing raw prompt."""
    db = SessionLocal()

    try:
        log = _build_guard_scan_log(user_id, prompt, result, ip_address=ip_address)

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
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
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

        response = ScanResponse(
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


@router.post(
    "/explain",
    response_model=ExplainResponse,
    tags=["LLM Guard"],
    summary="Explain a Guard verdict with token-level attribution",
    responses={
        200: {"description": "Per-token attribution + predicted class."},
        429: {"description": "Rate limited (10 explanations per minute per user)."},
        503: {
            "description": (
                "No fine-tuned classifier is loaded. Explainability requires "
                "a real model — the heuristic fallback can't produce Shapley "
                "values."
            )
        },
        504: {"description": "Explanation exceeded the 15s timeout budget."},
    },
)
async def explain_prompt(
    request: ExplainRequestModel,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return per-token attribution scores for the Guard's verdict.

    Used by the dashboard's audit view: a reviewer clicks 'Explain' on a
    flagged scan and gets back which tokens drove the decision, with
    char-level offsets into the original text for in-place highlighting.

    SHAP is the primary method (Shapley values via PartitionExplainer).
    LIME is an opt-in (``method="lime"``) for long inputs where SHAP is
    too slow.

    Rate limit: 10 requests per minute per user. Timeout: 15s. Inputs
    longer than 4000 chars are rejected at validation time.
    """
    import asyncio

    from app.modules.guard.explainer import (
        ExplainerUnavailable,
        get_explainer,
    )

    # Rate limit: reuse the shared limiter under a distinct key so explain
    # quota is independent of scan quota.
    limited, retry_after = guard_scan_rate_limiter.check_and_consume(
        key=f"guard:explain:{current_user.id}",
        limit=_ExplainRateLimitConfig.LIMIT,
        window_seconds=_ExplainRateLimitConfig.WINDOW_SECONDS,
        fail_closed=True,
    )
    if limited:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={
                "detail": (
                    f"Rate limit exceeded: {_ExplainRateLimitConfig.LIMIT} "
                    f"explanations per {_ExplainRateLimitConfig.WINDOW_SECONDS} "
                    "seconds per user."
                )
            },
            headers={"Retry-After": str(retry_after)},
        )

    try:
        explainer = get_explainer()
    except ExplainerUnavailable as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=str(exc),
        )

    try:
        # SHAP is CPU-bound and synchronous — run in a worker thread so
        # the event loop stays responsive and the timeout actually fires.
        result = await asyncio.wait_for(
            asyncio.to_thread(
                explainer.explain,
                request.text,
                method=request.method,
                max_evals=request.max_evals,
            ),
            timeout=_ExplainRateLimitConfig.TIMEOUT_SECONDS,
        )
    except asyncio.TimeoutError:
        raise HTTPException(
            status_code=status.HTTP_504_GATEWAY_TIMEOUT,
            detail=(
                f"Explanation exceeded {_ExplainRateLimitConfig.TIMEOUT_SECONDS}s. "
                "Try a shorter prompt or a lower `max_evals`."
            ),
        )
    except ValueError as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(exc))
    except Exception:
        logger.exception(
            "guard.explain.failed", extra={"user_id": current_user.id}
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An internal error occurred while generating the explanation.",
        )

    return result


@router.get("/health", tags=["LLM Guard"])
def guard_health():
    """Check whether the Guard module is available.

    Returns:
        A status payload describing the Guard module availability.
    """
    return {"module": "llm_guard", "status": "available"}


@router.get("/info", tags=["LLM Guard"])
def guard_info():
    """Return diagnostic information about the Guard module.

    Returns:
        A status payload containing device and model details.
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

class CursorPagination:
    """
    Simple cursor-based pagination helper:
    - stable ordering: (scanned_at DESC, id DESC)
    - base64 cursor: (scanned_at|id)
    """

    @staticmethod
    def encode(scanned_at: datetime, log_id: int) -> str:
        if scanned_at.tzinfo is None:
            scanned_at = scanned_at.replace(tzinfo=timezone.utc)
        else:
            scanned_at = scanned_at.astimezone(timezone.utc)

        raw = f"{scanned_at.isoformat(timespec='seconds')}|{log_id}"
        return base64.urlsafe_b64encode(raw.encode()).decode()

    @staticmethod
    def decode(cursor: str) -> tuple[datetime, int]:
        try:
            decoded = base64.urlsafe_b64decode(cursor.encode()).decode()
            ts, id_str = decoded.split("|")

            dt = datetime.fromisoformat(ts)
            
            if dt.tzinfo is None:
               dt = dt.replace(tzinfo=timezone.utc)
            else:
               dt = dt.astimezone(timezone.utc)

            return dt, int(id_str)

        except Exception:
            raise HTTPException(status_code=400, detail="Invalid cursor format")
    

    @staticmethod
    def apply_filters(query, cursor: Optional[str]):
        if not cursor:
            return query

        cursor_dt, cursor_id = CursorPagination.decode(cursor)

        return query.filter(
    or_(
        GuardScanLog.scanned_at < cursor_dt,
        and_(
            GuardScanLog.scanned_at == cursor_dt,
            GuardScanLog.id < cursor_id
        )
    )
)
    @staticmethod
    def apply_ordering(query):
        return query.order_by(
            GuardScanLog.scanned_at.desc(),
            GuardScanLog.id.desc(),
        )

    @staticmethod
    def paginate(query, limit: int):
        items = query.limit(limit + 1).all()

        next_cursor = None
        has_next = len(items) > limit
        items = items[:limit]
        if has_next and items:
           last = items[-1]
           next_cursor = CursorPagination.encode(last.scanned_at, last.id)

        return items, next_cursor

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

@router.get("/history", response_model=CursorPaginatedResponse[GuardScanLogResponse])
def get_guard_history(
    cursor: Optional[str] = Query(None, description="Pagination cursor"),
    limit: int = Query(20, ge=1, le=100),

    decision: Optional[str] = Query(None),
    intent: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),

    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current user's Guard scan history (cursor paginated)."""

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
        end_date,
    )

    query = db.query(GuardScanLog).filter(*filters)

    # cursor + ordering handled by helper
    query = CursorPagination.apply_filters(query, cursor)
    query = CursorPagination.apply_ordering(query)

    logs, next_cursor = CursorPagination.paginate(query, limit)

    return CursorPaginatedResponse(
    items=logs,
    limit=limit,
    next_cursor=next_cursor,
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
    
    for b in scans_per_day:
        b["count"] = (
        int(b.get("allow", 0) or 0)
        + int(b.get("sanitize", 0) or 0)
        + int(b.get("block", 0) or 0)
    )
        
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
    """Return the current user's Guard configuration.

    Args:
        current_user: Authenticated user whose Guard config is requested.

    Returns:
        The user's saved Guard configuration, or the default config.
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
    """Update the current user's Guard configuration.

    Args:
        config: Sanitization level and threshold values to persist.
        current_user: Authenticated user whose Guard config is being updated.

    Returns:
        A confirmation payload containing the saved configuration.

    Raises:
        HTTPException: If any configuration value is out of range.
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
    http_request: Request,
    background_tasks: BackgroundTasks,
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

@router.get("/config", tags=["LLM Guard"])
def get_guard_config(current_user: User = Depends(get_current_user)):
    """Return the current user's Guard configuration.

    Args:
        current_user: Authenticated user whose Guard config is requested.

    Returns:
        The user's saved Guard configuration, or the default config.
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
    """Update the current user's Guard configuration.

    Args:
        config: Sanitization level and threshold values to persist.
        current_user: Authenticated user whose Guard config is being updated.

    Returns:
        A confirmation payload containing the saved configuration.

    Raises:
        HTTPException: If any configuration value is out of range.
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

