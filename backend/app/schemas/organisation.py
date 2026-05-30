"""
Pydantic schemas for Organisation CRUD and member management.
"""

from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional, List
from datetime import datetime
import re

from app.models.organisation import OrgRole


# ---------------------------------------------------------------------------
# Org schemas
# ---------------------------------------------------------------------------

class OrgCreate(BaseModel):
    name: str = Field(..., min_length=2, max_length=255, description="Display name of the organisation")
    slug: Optional[str] = Field(
        None,
        min_length=2,
        max_length=255,
        description="URL-safe identifier (auto-generated from name if omitted)",
    )

    @field_validator("slug")
    @classmethod
    def validate_slug(cls, v: Optional[str]) -> Optional[str]:
        if v is None:
            return v
        if not re.match(r"^[a-z0-9]+(?:-[a-z0-9]+)*$", v):
            raise ValueError("Slug must be lowercase alphanumeric with hyphens only (e.g. 'my-org')")
        return v


class OrgUpdate(BaseModel):
    name: Optional[str] = Field(None, min_length=2, max_length=255)


class OrgResponse(BaseModel):
    id: int
    name: str
    slug: str
    owner_id: int
    created_at: datetime
    updated_at: datetime
    member_count: int = 0

    class Config:
        from_attributes = True


# ---------------------------------------------------------------------------
# Member schemas
# ---------------------------------------------------------------------------

class OrgMemberResponse(BaseModel):
    user_id: int
    email: str
    full_name: Optional[str]
    role: OrgRole
    joined_at: Optional[datetime]
    invited_at: datetime

    class Config:
        from_attributes = True


class InviteMemberRequest(BaseModel):
    email: EmailStr = Field(..., description="Email of an existing AegisAI user to invite")


class OrgMemberListResponse(BaseModel):
    members: List[OrgMemberResponse]
    total: int
