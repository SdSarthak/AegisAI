from datetime import datetime
from pydantic import BaseModel, Field


class GuardAuditLogResponse(BaseModel):
    id: int
    user_id: int
    prompt_hash: str = Field(..., min_length=64, max_length=64)
    decision: str
    threat_type: str
    confidence_score: float
    timestamp: datetime

    class Config:
        from_attributes = True
