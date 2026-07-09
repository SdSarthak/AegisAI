"""
Analytics API — compliance score timelines and aggregate stats.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

This module serves as the primary router for calculating, retrieving, and aggregating
analytics data relating to AI Systems and their associated regulatory compliance levels.

To assist backend maintainers in understanding the broader context of AegisAI's
regulatory ecosystem, this docstring details the compliance document generation architecture,
PDF export pipeline, and AI System database relationships.

================================================================================
                              ARCHITECTURE REVIEW
================================================================================

1. DOCUMENT GENERATION FLOW
---------------------------
AegisAI enables users to generate compliance documents dynamically for any registered
AI System via a robust, dual-path narrative compilation process:

* Request & System Validation:
  - Users request document generation for a specific AI System (via POST /api/v1/documents/generate).
  - The backend validates the existence and ownership of the target AI System to ensure strict tenant isolation.
  - It queries the database for the latest associated `RiskAssessment` record for the AI System to integrate
    risk findings into the final document content.

* Primary Narrative Generation (LLM-based):
  - The generator invokes `generate_compliance_narrative()`, which passes the AI System's metadata (e.g., sector,
    use case, system description), latest `RiskAssessment` details, and the current user's company information to
    a Large Language Model (LLM).
  - The LLM synthesizes these contexts into a highly tailored, natural language compliance narrative.

* Fallback Narrative Generation (Template-based):
  - If the LLM generation fails (e.g., due to API timeout, rate limits, or missing credentials), the system catches
    the error, logs a warning, and gracefully falls back to a deterministic, template-based generation.
  - It retrieves a pre-configured Markdown template matching the requested `DocumentType` from the `DOCUMENT_TEMPLATES` dictionary:
    * `TECHNICAL_DOCUMENTATION`: Technical architecture, data flows, and logging mechanisms.
    * `RISK_ASSESSMENT`: Comprehensive risk classification details, mitigation measures, and next steps.
    * `CONFORMITY_DECLARATION`: Official compliance declarations under specific EU AI Act articles.
  - The Markdown template is populated using standard Python string formatting (`template.format(...)`)
    with metadata extracted directly from the `AISystem` database record.

* Persistence:
  - Once the narrative text (either LLM-generated or template-derived) is ready, the system persists it
    by creating a new `Document` database record with `DocumentStatus.GENERATED` linked to the AI System.


2. PDF EXPORT WORKFLOW
----------------------
AegisAI provides users with the ability to export compliance documents as print-ready PDF files.
The backend integrates two distinct PDF rendering tools, each serving a unique role in the architecture:

* ReportLab (Programmatic Layout Builder):
  - Role: Programmatic layout creation.
  - ReportLab is used to dynamically construct PDFs from structured data. It compiles document elements
    (e.g., Headings, Paragraphs, Spacers, PageBreaks) into a sequence of "Flowables".
  - A custom Markdown-to-ReportLab parser reads stored document content line-by-line:
    - Heading characters (`#`, `##`, `###`) are mapped to custom styled Paragraphs with distinct hierarchy, colors, and font sizes.
    - Bullet points (`- `) are formatted with bullet flowables.
    - Double asterisks (`**text**`) are translated into ReportLab's HTML-like inline tags (`<b>text</b>`).
  - The final flowables list is processed by `SimpleDocTemplate` and drawn onto an A4 page layout inside a `BytesIO` buffer.
  - The exported PDF bytes are validated (verifying `%PDF-` magic bytes and size constraints) and returned as a FastAPI `StreamingResponse`.

* WeasyPrint (HTML-to-PDF Engine):
  - Role: High-fidelity document styling via standard CSS/HTML.
  - WeasyPrint operates as a visual rendering engine that compiles HTML documents styled with modern CSS
    (e.g., Tailwind CSS, print-specific CSS rules) directly into PDFs.
  - This is ideal for generating highly styled reports, badges, and certificates that require consistent
    visual layouts matching the frontend designs, without programmatically defining flowables.


3. AI SYSTEM DATABASE RELATIONSHIPS
-----------------------------------
The compliance documents are strictly linked to AI System entities in the relational database:

* Relational Schema:
  - There is a Many-to-One relationship between `Document` and `AISystem`.
  - Each `Document` record has a foreign key `ai_system_id` pointing to the `ai_systems` table.
  - An `AISystem` can have multiple documents of different types or generated versions over its lifecycle.
  - Both `Document` and `AISystem` maintain a Many-to-One relationship with `User` via `owner_id`. This
    ensures that document retrieval and modifications are restricted to the verified owner of the system.

* Relational Mapping:
  - In SQLAlchemy, the `Document` model is linked back to the `AISystem` model via a `relationship` block,
    allowing developers to access a system's documents through standard object-relational mapping (e.g., `ai_system.documents`).
  - This structure permits efficient cascading deletes (if an AI system is deleted, its related compliance
    documents are cleaned up) and clean auditing of a system's compliance lifecycle.

================================================================================

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
from app.models.compliance_snapshot import ComplianceSnapshot
from app.models.document import Document
from sqlalchemy import func
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import Query

from app.models.guard_scan_log import GuardScanLog
from app.schemas.audit_log import GuardAuditLogResponse
from app.schemas.pagination import PaginatedResponse

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


@router.get("/system-risk")
def get_system_risk(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Return per-system risk scores for the current user."""
    systems = (
        db.query(AISystem.id, AISystem.name, AISystem.compliance_score, AISystem.risk_level)
        .filter(AISystem.owner_id == current_user.id)
        .all()
    )
    return [
        {
            "id": system.id,
            "name": system.name,
            "risk_score": system.compliance_score if system.compliance_score is not None else 0,
            "risk_level": system.risk_level.value if system.risk_level else "unknown",
        }
        for system in systems
    ]


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
        since = datetime.now(timezone.utc) - timedelta(days=days)
        filters.append(GuardScanLog.scanned_at >= since)

    base_query = db.query(GuardScanLog).filter(*filters)
    total = base_query.count()
    logs = base_query.order_by(GuardScanLog.scanned_at.desc()).offset(skip).limit(limit).all()

    return PaginatedResponse(items=logs, total=total, skip=skip, limit=limit)
