from pydantic import BaseModel
from typing import Optional
from datetime import datetime


class ApiKeyCreate(BaseModel):
    name: str


class ApiKeyResponse(BaseModel):
    id: int
    name: str
    created_at: datetime
    revoked: bool
    revoked_at: datetime | None = None
    class Config:
        from_attributes = True


class ApiKeyGeneratedResponse(BaseModel):
    api_key: str
    name: str


class ApiKeyRevokeResponse(BaseModel):
    message: str