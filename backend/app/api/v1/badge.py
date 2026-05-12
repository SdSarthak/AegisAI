"""
Public Compliance Badge API — no authentication required.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

TODO for contributors (help wanted):
  - Implement GET /badge/{system_id} — return an SVG badge showing the
    AI system's current compliance status and risk level.
    This endpoint is PUBLIC (no JWT required) so organisations can embed
    the badge in their README or website.
  - The badge should show: system name, risk level, compliance status,
    and a color (green=compliant, yellow=in_progress, red=non_compliant).
  - Optionally support ?format=json to return machine-readable JSON instead.
  - Acceptance criteria: visiting /badge/{id} in a browser renders an
    SVG badge without requiring a login.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session
from app.core.database import get_db
from app.models.ai_system import AISystem
from app.modules.badge.badge_generator import generate_badge_svg

router = APIRouter()


@router.get("/{system_id}", tags=["Compliance Badge"])
def get_compliance_badge(
    system_id: int,
    format: str = "svg",  # "svg" | "json"
    db: Session = Depends(get_db),
):
    """
    Return a public compliance badge for an AI system.
    """
    system = db.query(AISystem).filter(AISystem.id == system_id).first()
    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="System not found"
        )

    if format == "json":
        return {
            "system_id": system_id,
            "name": system.name,
            "risk_level": system.risk_level,
            "compliance_status": system.compliance_status,
        }

    svg = generate_badge_svg(system.name, system.risk_level, system.compliance_status)
    return Response(content=svg, media_type="image/svg+xml")
