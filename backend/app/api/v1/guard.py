"""
LLM Guard API — exposes prompt injection scanning as a REST endpoint.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

TODO for contributors (medium difficulty):
  - Add per-user rate limiting on POST /guard/scan
  - Persist scan results to the database for audit logs
  - Add a GET /guard/stats endpoint returning block/allow/sanitize counts
"""

import hashlib
from collections import defaultdict, deque
from datetime import datetime, timedelta, timezone
from threading import Lock

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import require_role
from app.models.guard_scan_log import GuardScanLog
from app.models.user import User, UserRole
from app.schemas.guard_scan_log import GuardScanLogResponse
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


@router.post("/scan", response_model=ScanResponse)
def scan_prompt(
    request: ScanRequest,
    current_user: User = Depends(require_role(UserRole.ANALYST, UserRole.ADMIN)),
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

        log = GuardScanLog(
            user_id=current_user.id,
            prompt_hash=hashlib.sha256(request.prompt.encode()).hexdigest(),
            decision=result["decision"],
            confidence=result["metadata"]["decision_reasoning"]["confidence"],
            matched_patterns=result["metadata"]["regex_analysis"].get(
                "matched_patterns", []
            ),
        )
        db.add(log)
        db.commit()

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


@router.get("/config", tags=["LLM Guard"])
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
