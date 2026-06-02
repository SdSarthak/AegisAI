from pydantic import BaseModel
from datetime import datetime
from typing import Optional
from app.models.compliance_requirement import RequirementStatus


class ComplianceRequirementBase(BaseModel):
    requirement_id: str
    description: str
    article_reference: Optional[str] = None
    status: RequirementStatus = RequirementStatus.TODO


class ComplianceRequirementCreate(ComplianceRequirementBase):
    pass


class ComplianceRequirementUpdate(BaseModel):
    status: RequirementStatus


class ComplianceRequirementResponse(ComplianceRequirementBase):
    id: int
    ai_system_id: int
    updated_at: datetime

    model_config = {"from_attributes": True}