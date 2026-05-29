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
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.ai_system import AISystem, ComplianceStatus, RiskLevel
from app.models.user import User
from app.schemas.analytics import ComplianceTimelineResponse

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
