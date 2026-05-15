"""Pydantic schemas for integrations and gap analysis."""

from pydantic import BaseModel, SecretStr
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.integration import IntegrationType


class IntegrationSettingsCreate(BaseModel):
    """Request to create or update integration settings."""

    integration_type: IntegrationType
    base_url: str
    api_key: SecretStr
    username: Optional[str] = None
    project_key: Optional[str] = None  # Jira only
    team_id: Optional[str] = None  # Linear only
    create_on_high: bool = True
    create_on_unacceptable: bool = True
    create_gap_tickets: bool = False
    gap_ticket_template: Optional[Dict[str, str]] = None


class IntegrationSettingsResponse(BaseModel):
    """Response containing integration settings (without credentials)."""

    id: int
    user_id: int
    integration_type: IntegrationType
    base_url: str
    username: Optional[str]
    project_key: Optional[str]
    team_id: Optional[str]
    create_on_high: bool
    create_on_unacceptable: bool
    create_gap_tickets: bool
    gap_ticket_template: Dict[str, str]
    is_active: bool
    last_tested_at: Optional[datetime]
    test_result: Optional[str]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class IntegrationTestRequest(BaseModel):
    """Request to test integration connection."""

    integration_id: int


class IntegrationTestResponse(BaseModel):
    """Response from integration test."""

    success: bool
    message: str
    details: Optional[Dict[str, Any]] = None


class ComplianceGap(BaseModel):
    """Represents a single compliance gap."""

    gap_type: str  # e.g., "explainability", "oversight", "documentation"
    severity: str  # e.g., "high", "medium", "low"
    description: str
    recommendation: str
    affected_articles: List[str] = []  # e.g., ["Article 14", "Article 15"]


class GapAnalysisResponse(BaseModel):
    """Gap analysis results for an AI system."""

    ai_system_id: int
    risk_level: str
    compliance_status: str
    overall_compliance_score: float  # 0-100
    gaps: List[ComplianceGap]
    summary: str
    analysis_date: datetime

    class Config:
        from_attributes = True


class IntegrationTicketResponse(BaseModel):
    """Response for created ticket."""

    id: int
    external_ticket_id: str
    external_url: Optional[str]
    ticket_type: str
    link_reason: str
    gap_type: Optional[str]
    created_at: datetime

    class Config:
        from_attributes = True
