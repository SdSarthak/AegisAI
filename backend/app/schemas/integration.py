from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.integration import IntegrationType


class JiraIntegrationCreate(BaseModel):
    base_url: str
    email: str
    api_token: str
    project_key: str


class LinearIntegrationCreate(BaseModel):
    api_key: str
    team_id: str


class IntegrationResponse(BaseModel):
    id: int
    integration_type: IntegrationType
    base_url: Optional[str] = None
    email: Optional[str] = None
    project_key: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True