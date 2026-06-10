from typing import Literal, List

from pydantic import BaseModel


class ComplianceRequirementItem(BaseModel):
    requirement: str
    article_reference: str
    status: Literal["missing", "partial", "done"]
    action_needed: str

    model_config = {"from_attributes": True}


class ComplianceGapResponse(BaseModel):
    system_id: int
    system_name: str
    risk_level: str
    compliance_status: str
    total_requirements: int
    done_count: int
    partial_count: int
    missing_count: int
    requirements: List[ComplianceRequirementItem]
