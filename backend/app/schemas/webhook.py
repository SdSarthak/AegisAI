from __future__ import annotations

from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


class WebhookCreate(BaseModel):
    url: HttpUrl
    secret: Optional[str] = None
    events: list[str] = []  # e.g. ["guard_block", "compliance_drift"]


class WebhookResponse(BaseModel):
    id: int
    url: str
    is_active: bool
    events: list[str]
    created_at: datetime

    class Config:
        from_attributes = True
