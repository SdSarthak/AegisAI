"""
Analytics API — compliance score timelines and aggregate stats.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

TODO for contributors (help wanted):
  - Implement GET /analytics/compliance-timeline?system_id={id}&days=30
    Return the last N daily ComplianceSnapshot rows for one AI system.
  - Implement GET /analytics/summary — return overall stats:
    total systems, average compliance score, count by risk level,
    count by compliance status.
  - Acceptance criteria: after the daily snapshot scheduler runs (see
    backend/app/tasks/scheduler.py), the timeline endpoint returns at
    least one data point per system.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.ai_system import AISystem, RiskLevel, ComplianceStatus
from app.schemas.analytics import (
    ComplianceTimelineResponse,
    AnalyticsSummaryResponse,
    RiskDistributionValue,
)

router = APIRouter()


@router.get("/compliance-timeline", response_model=ComplianceTimelineResponse)
def get_compliance_timeline(
    system_id: int,
    days: int = 30,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return daily compliance snapshots for a given AI system.

    TODO (help wanted): query ComplianceSnapshot filtered by ai_system_id and
    snapshotted_at >= now - days. Verify the system belongs to current_user.
    """
    # TODO: implement — replace with real DB query
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED, detail="Not implemented yet"
    )


@router.get("/summary", response_model=AnalyticsSummaryResponse)
def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return aggregate compliance stats for the current user's systems.
    """
    systems = db.query(AISystem).filter(AISystem.owner_id == current_user.id).all()
    total_systems = len(systems)

    scores = [s.compliance_score for s in systems if s.compliance_score is not None]
    avg_compliance_score = round(sum(scores) / len(scores), 1) if scores else 0.0

    compliant_count = sum(1 for s in systems if s.compliance_status == ComplianceStatus.COMPLIANT)
    high_risk_count = sum(1 for s in systems if s.risk_level == RiskLevel.HIGH)

    # Initialize distribution counts
    risk_counts = {
        RiskLevel.MINIMAL: 0,
        RiskLevel.LIMITED: 0,
        RiskLevel.HIGH: 0,
        RiskLevel.UNACCEPTABLE: 0,
    }

    for s in systems:
        if s.risk_level in risk_counts:
            risk_counts[s.risk_level] += 1

    risk_distribution = [
        RiskDistributionValue(name="Minimal Risk", value=risk_counts[RiskLevel.MINIMAL]),
        RiskDistributionValue(name="Limited Risk", value=risk_counts[RiskLevel.LIMITED]),
        RiskDistributionValue(name="High Risk", value=risk_counts[RiskLevel.HIGH]),
        RiskDistributionValue(name="Unacceptable Risk", value=risk_counts[RiskLevel.UNACCEPTABLE]),
    ]

    return AnalyticsSummaryResponse(
        total_systems=total_systems,
        avg_compliance_score=avg_compliance_score,
        compliant_count=compliant_count,
        high_risk_count=high_risk_count,
        risk_distribution=risk_distribution,
    )

