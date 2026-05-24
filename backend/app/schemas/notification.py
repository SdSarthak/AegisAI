from __future__ import annotations

from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class NotificationResponse(BaseModel):
    id: int
    notification_type: str
    title: str
    message: str
    is_read: bool
    resource_type: Optional[str] = None
    resource_id: Optional[int] = None
    created_at: datetime

    class Config:
        from_attributes = True


class NotificationMarkRead(BaseModel):
    """Body for marking one or more notifications as read."""

    ids: list[int]
