"""
Analytics API — compliance score timelines and aggregate stats.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

TODO for contributors (help wanted):
  - Implement GET /analytics/compliance-timeline?system_id={id}&days=30
    Return the last N daily ComplianceSnapshot rows for one AI system.
  - Acceptance criteria: after the daily snapshot scheduler runs (see
    backend/app/tasks/scheduler.py), the timeline endpoint returns at
    least one data point per system.
"""
from datetime import datetime, timedelta
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.ai_system import AISystem, ComplianceStatus, RiskLevel
from app.models.compliance_snapshot import ComplianceSnapshot
from app.models.guard_scan_log import GuardScanLog
from app.models.user import User
from app.schemas.analytics import ComplianceTimelineResponse
from app.schemas.guard_scan_log import GuardScanLogResponse
from app.schemas.pagination import PaginatedResponse

router = APIRouter()


@router.get("/audit-logs", response_model=PaginatedResponse[GuardScanLogResponse])
def get_compliance_timeline(
    system_id: int,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return daily compliance snapshots for a single AI system.

    Args:
        system_id: ID of the AI system to inspect.
        days: Number of days of history to return.
        current_user: Authenticated user requesting the timeline.
        db: Database session used to query compliance snapshots.

    Returns:
        ComplianceTimelineResponse containing the system's daily compliance data.
    """
    system = (
        db.query(AISystem)
        .filter(AISystem.id == system_id, AISystem.owner_id == current_user.id)
        .one_or_none()
    )
    if system is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found or access denied",
        )

    cutoff = datetime.utcnow() - timedelta(days=days)
    snapshots = (
        db.query(ComplianceSnapshot)
        .filter(
            ComplianceSnapshot.ai_system_id == system_id,
            ComplianceSnapshot.snapshotted_at >= cutoff,
        )
        .order_by(ComplianceSnapshot.snapshotted_at.asc())
        .all()
    )

    return ComplianceTimelineResponse(
        ai_system_id=system.id,
        ai_system_name=system.name,
        snapshots=snapshots,
    )


@router.get("/summary")
def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return aggregate compliance statistics for the current user.

    Args:
        current_user: Authenticated user whose systems are being summarized.
        db: Database session used to aggregate compliance metrics.

    Returns:
        Aggregate compliance statistics for the user's AI systems.
    """
    systems = db.query(AISystem).filter(AISystem.owner_id == current_user.id).all()

    counts = {risk.value: 0 for risk in RiskLevel}
    compliance_statuses = {status.value: 0 for status in ComplianceStatus}
    scored_values: list[float] = []

    for system in systems:
        if system.risk_level:
            counts[system.risk_level.value] += 1
        if system.compliance_status:
            compliance_statuses[system.compliance_status.value] += 1
        if system.compliance_score is not None:
            scored_values.append(float(system.compliance_score))

    average_compliance_score = (
        round(sum(scored_values) / len(scored_values), 2) if scored_values else 0.0
    )

    return {
        "total_systems": len(systems),
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
