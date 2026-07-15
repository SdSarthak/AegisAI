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

    since = datetime.now(timezone.utc) - timedelta(days=days)

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

    # Systems with zero associated documents ("Documents Missing" widget stat).
    documents_missing = (
        db.query(func.count(AISystem.id))
        .outerjoin(Document, Document.ai_system_id == AISystem.id)
        .filter(AISystem.owner_id == current_user.id)
        .group_by(AISystem.id)
        .having(func.count(Document.id) == 0)
        .count()
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
        # Flat summary consumed by the dashboard's Compliance Progress
        # Summary Widget (issue #1341).
        "widget_summary": {
            "total": int(total_systems),
            "compliant": compliance_statuses.get("compliant", 0),
            "pending_review": compliance_statuses.get("under_review", 0),
            "high_risk": counts.get("high", 0),
            "documents_missing": int(documents_missing),
        },
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
