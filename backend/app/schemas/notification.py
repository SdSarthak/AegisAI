"""Pydantic schemas for notification payloads and update actions.

These models define the response body for notification APIs and the request
shape used when marking notifications as read.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel


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
    """Request body used to mark one or more notifications as read."""

    ids: list[int]
