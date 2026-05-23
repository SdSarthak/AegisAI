from __future__ import annotations

from datetime import datetime
from typing import List

from pydantic import BaseModel, HttpUrl


class WebhookConfigCreate(BaseModel):
    url: HttpUrl
    events: List[str]
    secret: str


class WebhookConfigOut(BaseModel):
    id: int
    url: str
    events: List[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
