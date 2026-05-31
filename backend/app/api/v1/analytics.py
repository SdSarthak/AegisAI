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

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.ai_system import AISystem, ComplianceStatus, RiskLevel
from app.models.user import User
from app.schemas.analytics import ComplianceTimelineResponse
from sqlalchemy import func
from app.models.ai_system import AISystem, RiskLevel
from app.models.guard_scan_log import GuardScanLog
from app.schemas.guard_scan_log import GuardScanLogResponse
from app.schemas.pagination import PaginatedResponse
from typing import Optional
from fastapi import Query
from datetime import datetime

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
    # TODO: implement — replace with real DB query
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet"
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


@router.get('/audit-logs')
def get_audit_logs(
    page: int = 1,
    page_size: int = 20,
    decision: str = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return paginated guard scan audit logs for the current user.

    Args:
        page: Page number, 1-indexed (default: 1).
        page_size: Number of results per page (default: 20).
        decision: Optional filter by decision (allow/sanitize/block).
        current_user: The authenticated user extracted from the JWT token.
        db: Database session dependency.

    Returns:
        dict: Paginated list of guard scan log entries.
    """
    from app.models.guard_scan_log import GuardScanLog

    query = db.query(GuardScanLog).filter(GuardScanLog.user_id == current_user.id)

    if decision:
        query = query.filter(GuardScanLog.decision == decision)

    total = query.count()
    logs = (
        query.order_by(GuardScanLog.scanned_at.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )

    return {
        "page": page,
        "page_size": page_size,
        "total": total,
        "logs": [
            {
                "id": log.id,
                "decision": log.decision,
                "confidence": log.confidence,
                "intent": log.intent,
                "detection_type": log.detection_type,
                "prompt_length": log.prompt_length,
                "scanned_at": log.scanned_at,
            }
            for log in logs
        ],
    }