"""Public API for compliance badges that can be embedded externally.

The badge endpoint is intentionally unauthenticated so a system's current
status can be embedded in READMEs, dashboards, and public project pages.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import Response
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import get_db
from app.core.rate_limit import badge_rate_limiter
from app.models.ai_system import AISystem
from app.modules.badge.badge_generator import generate_badge_svg

router = APIRouter()


@router.get("/{system_id}", tags=["Compliance Badge"])
def get_compliance_badge(
    system_id: int,
    format: str = "svg",  # "svg" | "json"
    db: Session = Depends(get_db),
):
    """Return a public compliance badge for an AI system.

    Args:
        system_id: ID of the AI system to render a badge for.
        format: Response format to return. ``svg`` renders the badge as an
            image, while ``json`` returns the badge metadata as a payload.
        db: Active database session used to look up the AI system.

    Returns:
        Either a JSON payload with badge metadata or an SVG response.

    Raises:
        HTTPException: If rate limiting is exceeded or the AI system does not
            exist.
    """
    # Rate limit: 5 requests per minute per system ID by default (sensitive, fail closed)
    limited, retry_after = badge_rate_limiter.check_and_consume(
        key=f"badge:gen:{system_id}",
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
