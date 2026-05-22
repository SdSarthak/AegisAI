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
from collections import defaultdict, deque, Counter
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import List, Optional, Dict

from fastapi import APIRouter, Depends, HTTPException, Query, status, BackgroundTasks
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db, SessionLocal
from app.core.security import get_current_user
from app.models.guard_scan_log import GuardScanLog
from app.models.user import User
from app.schemas.guard_scan_log import GuardScanLogResponse
from app.schemas.guard_stats import GuardStatsResponse
from app.schemas.pagination import PaginatedResponse

router = APIRouter()


_RATE_LIMIT_REQUESTS = 60
_RATE_LIMIT_WINDOW_SECONDS = 60
_scan_attempts_by_user: dict[int, deque[datetime]] = defaultdict(deque)
_rate_limit_lock = Lock()


class ScanRequest(BaseModel):
    prompt: str


class ScanResponse(BaseModel):
    decision: str  # "allow" | "sanitize" | "block"
    confidence: float
    reasoning: str
    sanitized_prompt: str | None = None
    matched_patterns: list[str] = []


def _check_rate_limit(user_id: int) -> tuple[bool, int]:
    """Return whether the user is limited and the seconds to retry after."""
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
                    (_RATE_LIMIT_WINDOW_SECONDS -
                     (now - attempts[0]).total_seconds())
                    + 0.999
                ),
            )
            return True, retry_after

        attempts.append(now)
        return False, 0


def log_scan(
    user_id: int,
    prompt: str,
    result: dict
):
    """Log scan details to database without storing raw prompt."""
    db = SessionLocal()
    try:
        regex_analysis = result.get("metadata", {}).get("regex_analysis", {})
        intent_analysis = result.get("metadata", {}).get("intent_analysis", {})
        decision_reasoning = result.get("metadata", {}).get("decision_reasoning", {})

        regex_flag = regex_analysis.get("flag", False)
        intent = intent_analysis.get("intent", "benign")
        
        # Detection type logic
        if not regex_flag and intent == "benign":
            detection_type = "none"
        elif regex_flag and intent == "benign":
            detection_type = "regex"
        elif not regex_flag and intent in ("suspicious", "malicious"):
            detection_type = "ml"
        else:  # regex_flag and intent in ("suspicious", "malicious")
            detection_type = "combined"

        log = GuardScanLog(
            user_id=user_id,
            prompt_hash=hashlib.sha256(prompt.encode()).hexdigest(),
            decision=result.get("decision", "allow"),
            confidence=decision_reasoning.get("confidence", 0.0),
            matched_patterns=regex_analysis.get("matched_patterns", []),
            # New metadata fields
            detection_type=detection_type,
            regex_flag=regex_flag,
            regex_score=regex_analysis.get("risk_score", 0.0),
            intent=intent,
            ml_confidence=intent_analysis.get("confidence", 0.0),
            combined_score=decision_reasoning.get("confidence", 0.0),
            prompt_length=len(prompt),
            scanned_at=datetime.utcnow()
        )
        db.add(log)
        db.commit()
    finally:
        db.close()


@router.post("/scan", response_model=ScanResponse)
def scan_prompt(
    request: ScanRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Scan a prompt for injection risks.
    Returns a decision: allow, sanitize, or block.
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
        from app.core.config import settings

        level_map = {
            "low": SanitizationLevel.LOW,
            "medium": SanitizationLevel.MEDIUM,
            "high": SanitizationLevel.HIGH,
        }
        san_level = level_map.get(
            settings.GUARD_SANITIZATION_LEVEL, SanitizationLevel.MEDIUM
        )
        guard = LLMGuard(sanitization_level=san_level)
        result = guard.guard(request.prompt)

        # Logging to database as a background task
        background_tasks.add_task(log_scan, current_user.id, request.prompt, result)

        return ScanResponse(
            decision=result["decision"],
            confidence=result["metadata"]["decision_reasoning"]["confidence"],
            reasoning=result["metadata"]["decision_reasoning"]["reasoning"],
            sanitized_prompt=None,
            matched_patterns=result["metadata"]["regex_analysis"].get(
                "matched_patterns", []
            ),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e)
        )


@router.get("/health", tags=["LLM Guard"])
def guard_health():
    """Check if the Guard module is available."""
    return {"module": "llm_guard", "status": "available"}


class GuardConfigRequest(BaseModel):
    sanitization_level: str
    malicious_threshold: float
    suspicious_threshold: float


@router.get("/history", response_model=PaginatedResponse[GuardScanLogResponse])
def get_guard_history(
    page: int = Query(1, ge=1, description="Page number (1-indexed)"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Return the current user's Guard scan history, newest first."""
    base_query = (
        db.query(GuardScanLog)
        .filter(GuardScanLog.user_id == current_user.id)
    )
    total = base_query.count()
    logs = (
        base_query
        .order_by(GuardScanLog.created_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )
    return PaginatedResponse(items=logs, total=total, page=page, limit=limit)


# Temporary in-memory config store
user_guard_configs = {}

VALID_SANITIZATION_LEVELS = {"low", "medium", "high"}


from sqlalchemy import func
from collections import Counter
from app.schemas.guard_stats import GuardStatsResponse

@router.get("/stats", response_model=GuardStatsResponse)
def get_guard_stats(
    window: str = Query("7d", pattern="^(24h|7d|30d|all)$"),
    user_id: Optional[int] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get Guard scan statistics for the specified window and user.
    Admins can query stats for any user; regular users only for themselves.
    """
    # Authorization check
    target_user_id = user_id if user_id is not None else current_user.id
    
    # Check if admin (instructions say .role == 'admin')
    is_admin = getattr(current_user, "role", None) == "admin"
    
    if target_user_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to query stats for another user."
        )

    # Calculate time window
    now = datetime.utcnow()
    if window == "24h":
        start_date = now - timedelta(hours=24)
    elif window == "7d":
        start_date = now - timedelta(days=7)
    elif window == "30d":
        start_date = now - timedelta(days=30)
    else:  # all
        start_date = None

    # Base query
    query = db.query(GuardScanLog).filter(GuardScanLog.user_id == target_user_id)
    if start_date:
        query = query.filter(GuardScanLog.scanned_at >= start_date)

    total_scans = query.count()

    # Breakdown by decision
    decision_counts = (
        db.query(GuardScanLog.decision, func.count(GuardScanLog.id))
        .filter(GuardScanLog.user_id == target_user_id)
    )
    if start_date:
        decision_counts = decision_counts.filter(GuardScanLog.scanned_at >= start_date)
    decision_counts = decision_counts.group_by(GuardScanLog.decision).all()
    
    by_decision = {
        "allow": {"count": 0, "pct": 0.0},
        "sanitize": {"count": 0, "pct": 0.0},
        "block": {"count": 0, "pct": 0.0}
    }
    for decision, count in decision_counts:
        if decision in by_decision:
            by_decision[decision]["count"] = count
            by_decision[decision]["pct"] = round((count / total_scans * 100), 1) if total_scans > 0 else 0.0

    # Breakdown by detection type
    detection_counts = (
        db.query(GuardScanLog.detection_type, func.count(GuardScanLog.id))
        .filter(GuardScanLog.user_id == target_user_id)
    )
    if start_date:
        detection_counts = detection_counts.filter(GuardScanLog.scanned_at >= start_date)
    detection_counts = detection_counts.group_by(GuardScanLog.detection_type).all()
    
    by_detection_type = {
        "none": {"count": 0, "pct": 0.0},
        "regex": {"count": 0, "pct": 0.0},
        "ml": {"count": 0, "pct": 0.0},
        "combined": {"count": 0, "pct": 0.0}
    }
    for d_type, count in detection_counts:
        if d_type in by_detection_type:
            by_detection_type[d_type]["count"] = count
            by_detection_type[d_type]["pct"] = round((count / total_scans * 100), 1) if total_scans > 0 else 0.0

    # Top matched patterns
    logs_with_patterns = query.filter(GuardScanLog.matched_patterns != []).all()
    all_patterns = []
    for log in logs_with_patterns:
        if isinstance(log.matched_patterns, list):
            all_patterns.extend(log.matched_patterns)
    
    pattern_counts = Counter(all_patterns).most_common(10)
    top_matched_patterns = [{"pattern": p, "count": c} for p, c in pattern_counts]

    # Scans per day
    daily_counts = (
        db.query(func.date(GuardScanLog.scanned_at).label("date"), func.count(GuardScanLog.id))
        .filter(GuardScanLog.user_id == target_user_id)
    )
    if start_date:
        daily_counts = daily_counts.filter(GuardScanLog.scanned_at >= start_date)
    daily_counts = daily_counts.group_by("date").order_by("date").all()
    
    scans_per_day = [{"date": str(d), "count": c} for d, c in daily_counts]

    return {
        "window": window,
        "total_scans": total_scans,
        "by_decision": by_decision,
        "by_detection_type": by_detection_type,
        "top_matched_patterns": top_matched_patterns,
        "scans_per_day": scans_per_day
    }
def get_guard_config(current_user: User = Depends(get_current_user)):
    """
    Get per-user guard configuration.
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
    """
    Update per-user guard configuration.
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


class BulkScanRequest(BaseModel):
    prompts: list[str]

    def validate_prompts(self):
        if len(self.prompts) > 50:
            raise ValueError("Maximum 50 prompts allowed per batch request.")
        return self


class BulkScanResponse(BaseModel):
    results: list[ScanResponse]
    total: int
    processed: int


@router.post("/scan/batch", response_model=BulkScanResponse)
def bulk_scan_prompts(
    request: BulkScanRequest,
    current_user: User = Depends(get_current_user),
):
    """
    Scan a batch of prompts (max 50) for injection risks.
    Processes sequentially to respect memory constraints.
    Returns a decision for each prompt.
    """
    if len(request.prompts) > 50:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Maximum 50 prompts allowed per batch request."
        )

    limited, retry_after = _check_rate_limit(current_user.id)
    if limited:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Please try again later."},
            headers={"Retry-After": str(retry_after)},
        )

    try:
        from app.modules.guard.llm_guard import LLMGuard
        from app.modules.guard.sanitizer import SanitizationLevel
        from app.core.config import settings

        level_map = {
            "low": SanitizationLevel.LOW,
            "medium": SanitizationLevel.MEDIUM,
            "high": SanitizationLevel.HIGH,
        }
        san_level = level_map.get(
            settings.GUARD_SANITIZATION_LEVEL, SanitizationLevel.MEDIUM)
        guard = LLMGuard(sanitization_level=san_level)

        results = []
        for prompt in request.prompts:
            result = guard.guard(prompt)
            results.append(ScanResponse(
                decision=result["decision"],
                confidence=result["metadata"]["decision_reasoning"]["confidence"],
                reasoning=result["metadata"]["decision_reasoning"]["reasoning"],
                sanitized_prompt=None,
                matched_patterns=result["metadata"]["regex_analysis"].get(
                    "matched_patterns", []),
            ))

        return BulkScanResponse(
            results=results,
            total=len(request.prompts),
            processed=len(results),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
