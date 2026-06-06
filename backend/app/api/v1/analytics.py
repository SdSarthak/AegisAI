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
from app.models.compliance_snapshot import ComplianceSnapshot
from sqlalchemy import func
from datetime import datetime, timedelta

router = APIRouter()


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
