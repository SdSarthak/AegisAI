"""
backend/app/schemas/audit_log.py
NEW FILE — create this from scratch.
"""
from datetime import datetime
from typing import Any, List, Optional
from uuid import UUID

from pydantic import BaseModel

from app.models.audit_log import ScanStatus

from typing import Dict, Any
from datetime import datetime


class AISystemAuditLogResponse(BaseModel):
    id: int
    ai_system_id: int
    changed_by_id: int
    old_values: Dict[str, Any]
    new_values: Dict[str, Any]
    changed_at: datetime

    class Config:
        from_attributes = True
class AuditLogResponse(BaseModel):
    id:               UUID
    user_id:          Optional[str]
    ip_address:       Optional[str]
    timestamp:        datetime
    raw_prompt:       str
    scan_status:      ScanStatus
    risk_score:       Optional[float]
    triggered_rules:  Optional[Any]
    detection_method: Optional[str]

    class Config:
        from_attributes = True  # Pydantic v2; use orm_mode=True for Pydantic v1


class AuditLogListResponse(BaseModel):
    items: List[AuditLogResponse]
    total: int
    skip:  int
    limit: int