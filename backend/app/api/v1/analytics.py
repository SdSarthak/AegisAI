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
from app.schemas.analytics import ComplianceTimelineResponse
from sqlalchemy import func
from app.models.ai_system import AISystem, RiskLevel

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


@router.get("/summary")
def get_analytics_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Return aggregate compliance stats for the current user's systems.

    TODO (help wanted): aggregate counts and averages from ai_systems table.
    """
    # Return aggregate counts by risk level for the current user's AI systems.
    # Keep this implementation minimal: counts for minimal/limited/high/unacceptable.
    counts = (
      db.query(AISystem.risk_level, func.count(AISystem.id))
      .filter(AISystem.owner_id == current_user.id)
      .group_by(AISystem.risk_level)
      .all()
    )

    # Map results into a predictable shape for the frontend.
    result = {
      "counts": {
        "minimal": 0,
        "limited": 0,
        "high": 0,
        "unacceptable": 0,
      }
    }

    for risk, cnt in counts:
      if risk is None:
        continue
      # risk is an enum member (RiskLevel) or its value; normalize by string.
      key = risk.value if hasattr(risk, "value") else str(risk)
      if key in result["counts"]:
        result["counts"][key] = int(cnt)

    return result
