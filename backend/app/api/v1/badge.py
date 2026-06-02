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

from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import Response, JSONResponse
from sqlalchemy.orm import Session
from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import badge_rate_limiter
from app.models.ai_system import AISystem
from app.modules.badge.badge_generator import generate_badge_svg

router = APIRouter()


@router.get("/{public_badge_id}", tags=["Compliance Badge"])
def get_compliance_badge(
    public_badge_id: str,
    request: Request,
    format: str = "svg",  # "svg" | "json"
    db: Session = Depends(get_db),
):
    """
    Return a public compliance badge for an AI system.
    """
    # Rate limit by IP (fail-closed: deny when Redis is unreachable)
    client_ip = request.client.host if request.client else "127.0.0.1"
    limited, retry_after = badge_rate_limiter.check_and_consume(
        key=f"badge:{client_ip}",
        limit=settings.BADGE_RATE_LIMIT_REQUESTS,
        window_seconds=settings.BADGE_RATE_LIMIT_WINDOW_SECONDS,
        fail_closed=True,
    )
    if limited:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded. Please try again in {retry_after} seconds.",
            headers={"Retry-After": str(retry_after)},
        )

    system = db.query(AISystem).filter(AISystem.public_badge_id == public_badge_id).first()
    if not system or not system.public_badge_enabled:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="System not found"
        )

    headers = {"Cache-Control": "public, max-age=3600"}

    if format == "json":
        return JSONResponse(
            content={
                "public_badge_id": system.public_badge_id,
                "name": system.name,
                "risk_level": system.risk_level.value if system.risk_level else None,
                "compliance_status": system.compliance_status.value if system.compliance_status else None,
            },
            headers=headers,
        )

    svg = generate_badge_svg(system.name, system.risk_level, system.compliance_status)
    return Response(content=svg, media_type="image/svg+xml", headers=headers)

