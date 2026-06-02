"""
Pydantic schemas for compliance drift monitoring (addresses issue #82).

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class MonitoringSettings(BaseModel):
    """Read view of an AI system's monitoring configuration."""

    monitoring_enabled: bool
    webhook_url: Optional[str] = None
    has_webhook_secret: bool = False  # never expose the secret itself


class MonitoringUpdate(BaseModel):
    """Patch payload for monitoring settings."""

    monitoring_enabled: Optional[bool] = None
    webhook_url: Optional[HttpUrl] = None
    rotate_secret: bool = False  # if true, generate a new HMAC secret


class WebhookSecretResponse(BaseModel):
    """Returned exactly once when a secret is generated/rotated."""

    webhook_secret: str = Field(
        ...,
        description=(
            "The HMAC secret for signing webhook payloads. Shown only once — "
            "store it now; it cannot be retrieved later."
        ),
    )


class DriftEventOut(BaseModel):
    """Read view of a single drift event."""

    id: int
    ai_system_id: int
    detected_at: datetime
    drift_type: str
    previous_risk_level: Optional[str] = None
    new_risk_level: Optional[str] = None
    previous_status: Optional[str] = None
    new_status: Optional[str] = None
    classifier_version: str
    notified_in_app: bool
    webhook_delivered_at: Optional[datetime] = None
    webhook_response_code: Optional[int] = None

    class Config:
        from_attributes = True


class DriftEventList(BaseModel):
    items: list[DriftEventOut]
    total: int


class ScanResult(BaseModel):
    """Returned from a manual `POST /admin/compliance/scan` trigger."""

    systems_scanned: int
    events_created: int
    duration_ms: float