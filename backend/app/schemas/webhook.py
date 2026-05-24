"""
Pydantic schemas for WebhookConfig resource.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, HttpUrl


class WebhookCreate(BaseModel):
    url: HttpUrl
    secret: Optional[str] = None
    events: list[str] = Field(default_factory=list)


class WebhookConfigCreate(BaseModel):
    url: HttpUrl
    events: List[str]
    secret: str


class WebhookResponse(BaseModel):
    id: int
    url: str
    is_active: bool
    events: list[str]
    created_at: datetime

    class Config:
        from_attributes = True


class WebhookConfigOut(BaseModel):
    id: int
    url: str
    events: List[str]
    is_active: bool
    created_at: datetime

    class Config:
        from_attributes = True
