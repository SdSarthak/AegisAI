from datetime import datetime
from typing import Dict, Any, List, Optional

from pydantic import BaseModel


class AISystemAuditLogResponse(BaseModel):
    id: int
    ai_system_id: int
    # Nullable: SET NULL on delete preserves the audit row after the
    # acting user is deleted.
    changed_by_id: Optional[int] = None
    old_values: Dict[str, Any]
    new_values: Dict[str, Any]
    changed_at: datetime

    class Config:
        from_attributes = True


class GuardAuditLogResponse(BaseModel):
    id: int
    # Nullable: SET NULL on delete preserves the scan log after the
    # scanning user is deleted.
    user_id: Optional[int] = None
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