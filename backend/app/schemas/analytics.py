"""
Pydantic schemas for compliance analytics / timeline data.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class ComplianceSnapshotResponse(BaseModel):
    ai_system_id: int
    compliance_score: Optional[float] = None
    compliance_status: str
    risk_level: str | None
    snapshotted_at: datetime

    class Config:
        from_attributes = True


class ComplianceTimelineResponse(BaseModel):
    """Timeline of daily compliance snapshots for one AI system."""
    ai_system_id: int
    ai_system_name: str
    snapshots: list[ComplianceSnapshotResponse]
