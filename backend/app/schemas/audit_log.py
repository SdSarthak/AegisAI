"""
backend/app/schemas/audit_log.py
NEW FILE — create this from scratch.
"""
from datetime import datetime
class GuardAuditLogResponse(BaseModel):
    id: int
    user_id: int
    prompt_hash: str
    decision: str
    confidence: float
    matched_patterns: List[str]
    detection_type: str
    regex_flag: bool
    regex_score: float
    intent: str
    ml_confidence: float
    combined_score: float
    prompt_length: Optional[int] = None
    ip_address: Optional[str] = None
    scanned_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True