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
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.ai_system import AISystem, ComplianceStatus, RiskLevel
from app.models.guard_scan_log import GuardScanLog
from app.models.user import User
from app.schemas.analytics import ComplianceTimelineResponse
from app.schemas.audit_log import GuardAuditLogResponse
from app.schemas.pagination import PaginatedResponse
from app.models.compliance_snapshot import ComplianceSnapshot

router = APIRouter()


@router.get("/compliance-timeline", response_model=ComplianceTimelineResponse)
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
    """Return aggregate compliance statistics for the current user.

    Args:
        current_user: Authenticated user whose systems are being summarized.
        db: Database session used to aggregate compliance metrics.

    Returns:
        Aggregate compliance statistics for the user's AI systems.
    """
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
    user_id: Optional[int] = Query(None, description="Filter by user ID"),
    decision: Optional[str] = Query(None, pattern="^(allow|sanitize|block)$"),
    days: int = Query(7, ge=1, le=365, description="Number of days of history"),
    skip: int = Query(0, ge=0, description="Items to skip"),
    limit: int = Query(20, ge=1, le=100, description="Items per page"),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return paginated guard scan audit logs. Admin-only access.

    Args:
        user_id: Optional filter by specific user ID.
        decision: Optional filter by scan decision (allow, sanitize, block).
        days: Number of days of history to include (default 7).
        skip: Number of items to skip for pagination.
        limit: Maximum number of logs to include per page.
        current_user: Authenticated user (must be admin).
        db: Database session used to query audit logs.

    Returns:
        PaginatedResponse containing guard scan audit logs.

    Raises:
        HTTPException: If the caller is not an admin.
    """
    is_admin = getattr(current_user, "role", None) == "admin"
    if not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only admins can access audit logs.",
        )

    since = datetime.utcnow() - timedelta(days=days)

    query = db.query(GuardScanLog).filter(GuardScanLog.scanned_at >= since)

    if user_id is not None:
        query = query.filter(GuardScanLog.user_id == user_id)
    if decision is not None:
        query = query.filter(GuardScanLog.decision == decision)

    total = query.count()
    logs = (
        query.order_by(GuardScanLog.scanned_at.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )

    return PaginatedResponse(items=logs, total=total, skip=skip, limit=limit)
