from pydantic import BaseModel, Field
from typing import List, Any
from datetime import datetime


class GuardScanLogCreate(BaseModel):
    user_id: int
    prompt_hash: str = Field(..., min_length=64, max_length=64, description="SHA-256 hex digest of the scanned prompt")
    decision: str = Field(..., pattern="^(allow|sanitize|block)$")
    confidence: float = Field(..., ge=0.0, le=1.0)
    matched_patterns: List[Any] = []


class GuardScanLogResponse(BaseModel):
    id: int
    user_id: int
    prompt_hash: str
    decision: str
    confidence: float
    matched_patterns: List[Any]
    created_at: datetime

    class Config:
        from_attributes = True

class GuardStatsResponse(BaseModel):
    total_scans: int
    blocked: int
    sanitized: int
    allowed: int
    block_rate: float