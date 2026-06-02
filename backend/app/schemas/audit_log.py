from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel


class AISystemAuditLogResponse(BaseModel):
    id: int
    ai_system_id: int
    changed_by_id: int
    old_values: Dict[str, Any]
    new_values: Dict[str, Any]
    changed_at: datetime

    class Config:
        from_attributes = True


class GuardAuditLogResponse(BaseModel):
    id: int
    user_id: int
    prompt_hash: str
    decision: str
    confidence: float
    matched_patterns: List[Any]
    detection_type: str
    intent: str
    ip_address: Optional[str] = None
    scanned_at: datetime
    created_at: datetime

    class Config:
        from_attributes = True