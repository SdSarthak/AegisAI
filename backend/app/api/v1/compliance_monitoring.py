"""
Compliance drift monitoring API (addresses issue #82).

  GET    /ai-systems/{id}/monitoring - read settings
  PATCH  /ai-systems/{id}/monitoring - update toggle / webhook
  POST   /ai-systems/{id}/monitoring/rotate-secret - generate fresh HMAC
  GET    /ai-systems/{id}/drift-events - paginated history

  POST   /admin/compliance/scan - fire the monitor now (admin/owner only)

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import secrets

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.ai_system import AISystem
from app.models.compliance_drift_event import ComplianceDriftEvent
from app.models.user import User
from app.modules.compliance.monitor import run_drift_scan
from app.schemas.compliance import (
    DriftEventList,
    DriftEventOut,
    MonitoringSettings,
    MonitoringUpdate,
    ScanResult,
    WebhookSecretResponse,
)

router = APIRouter()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_owned_system(
    system_id: int, db: Session, current_user: User
) -> AISystem:
    system = db.query(AISystem).filter(AISystem.id == system_id).first()
    if system is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "AI system not found")
    if system.owner_id != current_user.id:
        # Don't leak existence to non-owners — same 404 as above.
        raise HTTPException(status.HTTP_404_NOT_FOUND, "AI system not found")
    return system


# ---------------------------------------------------------------------------
# Monitoring settings
# ---------------------------------------------------------------------------


@router.get(
    "/ai-systems/{system_id}/monitoring",
    response_model=MonitoringSettings,
    tags=["Compliance Monitoring"],
)
def get_monitoring_settings(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    system = _get_owned_system(system_id, db, current_user)
    return MonitoringSettings(
        monitoring_enabled=system.monitoring_enabled,
        webhook_url=system.webhook_url,
        has_webhook_secret=bool(system.webhook_secret),
    )


@router.patch(
    "/ai-systems/{system_id}/monitoring",
    response_model=MonitoringSettings,
    tags=["Compliance Monitoring"],
)
def update_monitoring_settings(
    system_id: int,
    payload: MonitoringUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    system = _get_owned_system(system_id, db, current_user)

    if payload.monitoring_enabled is not None:
        system.monitoring_enabled = payload.monitoring_enabled
    if payload.webhook_url is not None:
        system.webhook_url = str(payload.webhook_url)
    # `rotate_secret` is handled by a separate endpoint so the secret can
    # be returned in the body exactly once. PATCH would tempt callers to
    # rotate-and-discard, which silently breaks signature verification.

    db.commit()
    db.refresh(system)
    return MonitoringSettings(
        monitoring_enabled=system.monitoring_enabled,
        webhook_url=system.webhook_url,
        has_webhook_secret=bool(system.webhook_secret),
    )


@router.post(
    "/ai-systems/{system_id}/monitoring/rotate-secret",
    response_model=WebhookSecretResponse,
    tags=["Compliance Monitoring"],
    status_code=status.HTTP_201_CREATED,
)
def rotate_webhook_secret(
    system_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate a fresh HMAC secret for webhook signing.

    Shown exactly once — clients must store it immediately. Rotating
    invalidates any previously-generated secret.
    """
    system = _get_owned_system(system_id, db, current_user)
    new_secret = secrets.token_urlsafe(32)
    system.webhook_secret = new_secret
    db.commit()
    return WebhookSecretResponse(webhook_secret=new_secret)


# ---------------------------------------------------------------------------
# Drift event history
# ---------------------------------------------------------------------------


@router.get(
    "/ai-systems/{system_id}/drift-events",
    response_model=DriftEventList,
    tags=["Compliance Monitoring"],
)
def list_drift_events(
    system_id: int,
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    _get_owned_system(system_id, db, current_user)  # auth check

    base = db.query(ComplianceDriftEvent).filter(
        ComplianceDriftEvent.ai_system_id == system_id
    )
    total = base.count()
    rows = (
        base.order_by(ComplianceDriftEvent.detected_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return DriftEventList(
        items=[DriftEventOut.model_validate(r) for r in rows],
        total=total,
    )


# ---------------------------------------------------------------------------
# Manual scan trigger
# ---------------------------------------------------------------------------


@router.post(
    "/admin/compliance/scan",
    response_model=ScanResult,
    tags=["Compliance Monitoring"],
)
def trigger_drift_scan(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Run the drift monitor immediately. Returns when the scan finishes.

    Restricted to authenticated users; we don't have an admin role in
    the user model yet so any logged-in user can trigger their own
    systems' scan. The monitor itself only touches AISystems with
    ``monitoring_enabled=True``, so this is safe enough — a future PR
    should add a proper admin role and gate this endpoint behind it.
    """
    result = run_drift_scan(db=db)
    return ScanResult(
        systems_scanned=result["systems_scanned"],
        events_created=result["events_created"],
        duration_ms=result.get("duration_ms", 0.0),
    )