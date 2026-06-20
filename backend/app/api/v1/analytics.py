"""
Analytics API — compliance score timelines, aggregate stats, and API usage dashboard.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

TODO for contributors (help wanted):
  - Implement GET /analytics/compliance-timeline?system_id={id}&days=30
    Return the last N daily ComplianceSnapshot rows for one AI system.
  - Acceptance criteria: after the daily snapshot scheduler runs (see
    backend/app/tasks/scheduler.py), the timeline endpoint returns at
    least one data point per system.
"""

import json
import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db, get_redis
from app.core.security import get_current_user
from app.models.ai_system import AISystem, ComplianceStatus, RiskLevel
from app.models.user import User
from app.schemas.analytics import ComplianceTimelineResponse
from app.models.compliance_snapshot import ComplianceSnapshot
from datetime import datetime, timedelta
from typing import Optional
from zoneinfo import ZoneInfo

from fastapi import Query

from app.models.guard_scan_log import GuardScanLog
from app.schemas.audit_log import GuardAuditLogResponse
from app.schemas.pagination import PaginatedResponse

router = APIRouter()
logger = logging.getLogger(__name__)

ENDPOINT_DEFINITIONS = [
    {"name": "Guard Scan", "key": "guard_scan", "limit": 1000},
    {"name": "RAG Query", "key": "rag_query", "limit": 500},
    {"name": "AI System CRUD", "key": "ai_systems", "limit": 2000},
    {"name": "Document Operations", "key": "documents", "limit": 1000},
    {"name": "Classification", "key": "classification", "limit": 500},
]


def track_api_usage(user_id: int, endpoint_key: str) -> None:
    """Increment the daily usage counter for a user and endpoint in Redis."""
    try:
        r = get_redis()
        if r is None:
            return
        today = datetime.utcnow().date().isoformat()
        usage_key = f"usage:{user_id}:{today}"
        r.hincrby(usage_key, endpoint_key, 1)
        r.expire(usage_key, 172800)
    except Exception:
        logger.exception("Failed to track API usage for %s", endpoint_key)


def log_rate_limit_event(user_id: int, endpoint: str) -> None:
    """Push a rate-limit event to the user's recent-429 list in Redis."""
    try:
        r = get_redis()
        if r is None:
            return
        event = json.dumps({"endpoint": endpoint, "timestamp": datetime.utcnow().isoformat()})
        r.lpush(f"rate_limit_events:{user_id}", event)
        r.ltrim(f"rate_limit_events:{user_id}", 0, 49)
        r.expire(f"rate_limit_events:{user_id}", 604800)
    except Exception:
        logger.exception("Failed to log rate limit event")


@router.get("/compliance-timeline", response_model=ComplianceTimelineResponse)
def get_compliance_timeline(
    system_id: int,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return daily compliance snapshots for a single AI system."""
    system = db.query(AISystem).filter(
        AISystem.id == system_id,
        AISystem.owner_id == current_user.id
    ).first()

    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found"
        )

    since = datetime.utcnow() - timedelta(days=days)

    snapshots = db.query(ComplianceSnapshot).filter(
        ComplianceSnapshot.ai_system_id == system_id,
        ComplianceSnapshot.snapshotted_at >= since
    ).order_by(ComplianceSnapshot.snapshotted_at.asc()).all()

    return ComplianceTimelineResponse(
        ai_system_id=system.id,
        ai_system_name=system.name,
        snapshots=snapshots
    )


@router.get("/summary")
def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return aggregate compliance statistics for the current user."""
    # FIX: use SQL GROUP BY instead of loading all rows into memory
    risk_rows = (
        db.query(AISystem.risk_level, func.count(AISystem.id))
        .filter(AISystem.owner_id == current_user.id)
        .group_by(AISystem.risk_level)
        .all()
    )

    compliance_rows = (
        db.query(AISystem.compliance_status, func.count(AISystem.id))
        .filter(AISystem.owner_id == current_user.id)
        .group_by(AISystem.compliance_status)
        .all()
    )

    score_row = (
        db.query(func.avg(AISystem.compliance_score))
        .filter(
            AISystem.owner_id == current_user.id,
            AISystem.compliance_score.isnot(None),
        )
        .scalar()
    )

    total_systems = (
        db.query(func.count(AISystem.id))
        .filter(AISystem.owner_id == current_user.id)
        .scalar()
        or 0
    )

    counts = {risk.value: 0 for risk in RiskLevel}
    for risk_level, count in risk_rows:
        if risk_level:
            key = risk_level.value if hasattr(risk_level, "value") else str(risk_level)
            if key in counts:
                counts[key] = int(count)

    compliance_statuses = {s.value: 0 for s in ComplianceStatus}
    for compliance_status, count in compliance_rows:
        if compliance_status:
            key = (
                compliance_status.value
                if hasattr(compliance_status, "value")
                else str(compliance_status)
            )
            if key in compliance_statuses:
                compliance_statuses[key] = int(count)

    average_compliance_score = round(float(score_row), 2) if score_row else 0.0

    return {
        "total_systems": int(total_systems),
        "average_compliance_score": average_compliance_score,
        "counts": counts,
        "compliance_statuses": compliance_statuses,
    }


@router.get("/audit-logs", response_model=PaginatedResponse[GuardAuditLogResponse])
def get_audit_logs(
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    decision: Optional[str] = Query(None, pattern="^(allow|sanitize|block)$", description="Filter by decision"),
    days: Optional[int] = Query(None, ge=1, description="Only include logs from the last N days"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return guard scan audit logs with pagination and optional filters."""
    is_admin = getattr(current_user, "role", None) == "admin"
    if user_id is not None and user_id != current_user.id and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="You do not have permission to query audit logs for another user.",
        )

    target_user_id = user_id if user_id is not None else current_user.id
    filters = [GuardScanLog.user_id == target_user_id]

    if decision:
        filters.append(GuardScanLog.decision == decision)
    if days:
        since = datetime.utcnow() - timedelta(days=days)
        filters.append(GuardScanLog.scanned_at >= since)

    base_query = db.query(GuardScanLog).filter(*filters)
    total = base_query.count()
    logs = base_query.order_by(GuardScanLog.scanned_at.desc()).offset(skip).limit(limit).all()

    return PaginatedResponse(items=logs, total=total, skip=skip, limit=limit)


@router.get("/usage")
def get_api_usage(
    current_user: User = Depends(get_current_user),
):
    """Return aggregated API usage stats for the current user.

    Reads daily counters and rate-limit events from Redis. Returns empty/zero
    data when Redis is unavailable so the frontend always has a valid response.
    """
    user_id = current_user.id
    today = datetime.utcnow().date().isoformat()
    usage_key = f"usage:{user_id}:{today}"
    r = get_redis()

    daily_data: dict[str, int] = {}
    if r is not None:
        try:
            raw = r.hgetall(usage_key)
            daily_data = {k: int(v) for k, v in raw.items()} if raw else {}
        except Exception:
            logger.exception("Failed to read daily usage from Redis")

    endpoint_stats = []
    total_requests = 0
    total_limit = 0

    for ep in ENDPOINT_DEFINITIONS:
        count = daily_data.get(ep["key"], 0)
        total_requests += count
        total_limit += ep["limit"]
        reset_at = (
            datetime.utcnow()
            + timedelta(days=1)
        ).replace(hour=0, minute=0, second=0, microsecond=0).isoformat()
        endpoint_stats.append({
            "endpoint": ep["name"],
            "requests": count,
            "limit": ep["limit"],
            "remaining": max(0, ep["limit"] - count),
            "reset_at": reset_at,
        })

    history: list[dict] = []
    if r is not None:
        try:
            for i in range(7):
                day = (datetime.utcnow() - timedelta(days=i)).date().isoformat()
                day_key = f"usage:{user_id}:{day}"
                raw = r.hgetall(day_key)
                if raw:
                    day_total = sum(int(v) for v in raw.values())
                else:
                    day_total = 0
                history.append({"date": day, "requests": day_total})
            history.reverse()
        except Exception:
            logger.exception("Failed to read usage history from Redis")

    recent_429s: list[dict] = []
    if r is not None:
        try:
            events = r.lrange(f"rate_limit_events:{user_id}", 0, 9)
            if events:
                for event in events:
                    try:
                        recent_429s.append(json.loads(event))
                    except json.JSONDecodeError:
                        continue
        except Exception:
            logger.exception("Failed to read rate limit events from Redis")

    guard_scan_count = daily_data.get("guard_scan", 0)
    rag_query_count = daily_data.get("rag_query", 0)

    return {
        "daily": {
            "total_requests": total_requests,
            "total_limit": total_limit,
            "remaining": max(0, total_limit - total_requests),
            "reset_at": (
                datetime.utcnow()
                + timedelta(days=1)
            ).replace(hour=0, minute=0, second=0, microsecond=0).isoformat(),
        },
        "endpoints": endpoint_stats,
        "history": history,
        "recent_429s": recent_429s,
        "guard_scan": {
            "requests": guard_scan_count,
            "limit": 1000,
            "ai_credits_used": round(guard_scan_count * 0.5, 1),
        },
        "rag_query": {
            "requests": rag_query_count,
            "limit": 500,
            "estimated_tokens": rag_query_count * 1500,
        },
    }
