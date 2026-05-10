from pydantic import BaseModel
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.ai_system import RiskLevel, ComplianceStatus


class AISystemCreate(BaseModel):
    name: str
    description: Optional[str] = None
    version: Optional[str] = None
    use_case: Optional[str] = None
    sector: Optional[str] = None


class AISystemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    version: Optional[str] = None
    use_case: Optional[str] = None
    sector: Optional[str] = None
    questionnaire_responses: Optional[Dict[str, Any]] = None


class AISystemResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    version: Optional[str]
    use_case: Optional[str]
    sector: Optional[str]
    risk_level: Optional[RiskLevel]
    compliance_status: ComplianceStatus
    compliance_score: Optional[float] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# Risk Classification
class RiskClassificationRequest(BaseModel):
    """Questionnaire for EU AI Act risk classification."""
    
    # Basic use case
    use_case_category: str  # "hr_recruitment", "credit_scoring", "healthcare", etc.
    
    # High-risk indicators (Article 6)
    is_safety_component: bool = False  # Part of a safety component of a product
    affects_fundamental_rights: bool = False  # Employment, education, essential services
    uses_biometric_data: bool = False
    makes_automated_decisions: bool = True  # Decisions without human review
    
    # Specific high-risk areas (Annex III)
    hr_recruitment_screening: bool = False  # CV filtering, candidate ranking
    hr_promotion_termination: bool = False  # Promotion/termination decisions
    credit_worthiness: bool = False
    insurance_risk_assessment: bool = False
    law_enforcement: bool = False
    border_control: bool = False
    justice_system: bool = False
    
    # Transparency (Article 52)
    interacts_with_humans: bool = True  # Chatbots, virtual assistants
    generates_synthetic_content: bool = False  # Deepfakes, AI-generated media
    emotion_recognition: bool = False
    biometric_categorization: bool = False


class RiskClassificationResponse(BaseModel):
    risk_level: RiskLevel
    confidence: float  # 0-1
    reasons: List[str]
    requirements: List[str]
    next_steps: List[str]


class RiskAssessmentResponse(BaseModel):
    id: int
    ai_system_id: int
    assessment_type: str
    risk_level: RiskLevel
    overall_score: int
    data_governance_score: Optional[int]
    transparency_score: Optional[int]
    human_oversight_score: Optional[int]
    robustness_score: Optional[int]
    findings: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    assessed_at: datetime

    class Config:
        from_attributes = True


# Bulk Import
class BulkImportResponse(BaseModel):
    created: int
    errors: List[Dict[str, Any]]
