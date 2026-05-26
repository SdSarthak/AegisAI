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
