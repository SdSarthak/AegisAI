from __future__ import annotations

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


class RiskDistributionValue(BaseModel):
    name: str
    value: int


class AnalyticsSummaryResponse(BaseModel):
    total_systems: int
    avg_compliance_score: float
    compliant_count: int
    high_risk_count: int
    risk_distribution: list[RiskDistributionValue]

