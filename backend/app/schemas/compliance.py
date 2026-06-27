from __future__ import annotations
import re
from typing import Literal, List
from pydantic import BaseModel, field_validator

class ComplianceRequirementItem(BaseModel):
    requirement: str
    article_reference: str
    status: Literal["missing", "partial", "done"]
    action_needed: str
    
    model_config = {"from_attributes": True}

    @field_validator("requirement", "article_reference", "action_needed", mode="before")
    @classmethod
    def sanitize_strings(cls, value: any) -> any:
        if isinstance(value, str):
            # 1. Trim leading and trailing whitespaces
            cleaned = value.strip()
            # 2. Convert multiple internal spaces/newlines/tabs into a single space
            cleaned = re.sub(r'\s+', ' ', cleaned)
            return cleaned
        return value

class ComplianceGapResponse(BaseModel):
    system_id: int
    system_name: str
    risk_level: str
    compliance_status: str
    total_requirements: int
    done_count: int
    partial_count: int
    missing_count: int
    requirements: list[ComplianceRequirementItem]