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
    """Return daily compliance snapshots for a given AI system.

    Args:
        system_id: The unique identifier of the AI system to query.
        days: Number of past days to include in the timeline (default: 30).
        current_user: The authenticated user extracted from the JWT token.
        db: Database session dependency.

    Returns:
        ComplianceTimelineResponse: A list of daily compliance snapshot
            data points for the specified AI system.

    Raises:
        HTTPException: 501 if the endpoint is not yet implemented.
        HTTPException: 403 if the system does not belong to current_user.
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
    """Return aggregate compliance statistics for the current user's systems.

    Args:
        current_user: The authenticated user extracted from the JWT token.
        db: Database session dependency.

    Returns:
        dict: Aggregated stats including total systems, average compliance
            score, count by risk level, and count by compliance status.

    Raises:
        HTTPException: 501 if the endpoint is not yet implemented.
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
@router.get("/audit-logs", response_model=PaginatedResponse[GuardScanLogResponse])
def get_audit_logs(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    decision: Optional[str] = Query(None),
    start_date: Optional[datetime] = Query(None),
    end_date: Optional[datetime] = Query(None),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return paginated guard scan audit logs for the current user.

    Args:
        page: Page number, 1-indexed (default: 1).
        limit: Number of items per page, max 100 (default: 20).
        decision: Optional filter - allow, sanitize, or block.
        start_date: Optional start of date range filter.
        end_date: Optional end of date range filter.
        current_user: The authenticated user extracted from the JWT token.
        db: Database session dependency.

    Returns:
        PaginatedResponse[GuardScanLogResponse]: Paginated audit log entries.

    Raises:
        HTTPException: 400 if start_date is after end_date or decision is invalid.
    """
    VALID_DECISIONS = {"allow", "sanitize", "block"}

    if decision and decision.strip().lower() not in VALID_DECISIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid decision filter. Must be allow, sanitize, or block.",
        )

    if start_date and end_date and start_date > end_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="start_date cannot be after end_date.",
        )

    filters = [GuardScanLog.user_id == current_user.id]

    if decision:
        filters.append(GuardScanLog.decision == decision.strip().lower())
    if start_date:
        filters.append(GuardScanLog.scanned_at >= start_date)
    if end_date:
        filters.append(GuardScanLog.scanned_at <= end_date)

    query = db.query(GuardScanLog).filter(*filters)
    total = query.count()
    logs = (
        query.order_by(GuardScanLog.scanned_at.desc())
        .offset((page - 1) * limit)
        .limit(limit)
        .all()
    )

    return PaginatedResponse(
        items=logs,
        total=total,
        page=page,
        limit=limit,
    )