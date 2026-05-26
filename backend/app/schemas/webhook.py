from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl


class WebhookCreate(BaseModel):
    url: HttpUrl
    secret: Optional[str] = None
    events: list[str] = Field(default_factory=list)


class WebhookResponse(BaseModel):
    id: int
    url: str
    is_active: bool
    events: list[str]
    created_at: datetime

    class Config:
        from_attributes = True