from datetime import datetime
from typing import Dict, Any

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