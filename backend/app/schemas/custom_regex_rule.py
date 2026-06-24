from datetime import datetime

from pydantic import BaseModel, Field


class CustomRegexRuleCreate(BaseModel):
    pattern: str = Field(..., min_length=1, max_length=512)
    name: str = Field(..., min_length=1, max_length=128)
    severity: str = Field(default="medium", pattern=r"^(low|medium|high)$")


class CustomRegexRuleUpdate(BaseModel):
    is_active: bool


class CustomRegexRuleResponse(BaseModel):
    id: int
    user_id: int
    pattern: str
    name: str
    severity: str
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}
