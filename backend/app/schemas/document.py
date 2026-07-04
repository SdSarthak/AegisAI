import json
from typing import Any, Optional

from pydantic import BaseModel, field_validator
from datetime import datetime
from app.models.document import DocumentType, DocumentStatus

class DocumentShareResponse(BaseModel):
    share_url: str
    expires_in_days: int

class DocumentCreate(BaseModel):
    title: str
    document_type: DocumentType
    ai_system_id: Optional[int] = None
    content: Optional[str] = None


class DocumentUpdate(BaseModel):
    title: Optional[str] = None
    content: Optional[str] = None
    status: Optional[DocumentStatus] = None

class DocumentUpdateRequest(BaseModel):
    """Request to update document content only."""
    content: str

class DocumentTemplateResponse(BaseModel):
    """Available document template metadata for generation."""

    type: DocumentType
    name: str
    description: str

class DocumentResponse(BaseModel):
    id: int
    title: str
    document_type: DocumentType
    status: DocumentStatus
    content: Optional[str | dict[str, Any]]
    file_path: Optional[str]
    version: str
    ai_system_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True

    @field_validator("content", mode="before")
    @classmethod
    def parse_json_content(cls, value):
        if not isinstance(value, str):
            return value

        stripped = value.strip()
        if not stripped.startswith("{"):
            return value

        try:
            parsed = json.loads(stripped)
        except json.JSONDecodeError:
            return value

        return parsed if isinstance(parsed, dict) else value


class DocumentGenerateRequest(BaseModel):
    """Request to generate a compliance document."""

    document_type: DocumentType
    ai_system_id: int
    include_recommendations: bool = True


class DocumentVersionResponse(BaseModel):
    id: int
    document_id: int
    version_number: str
    created_at: datetime
    regeneration_reason: Optional[str] = None

    class Config:
        from_attributes = True


class DiffHunkLine(BaseModel):
    type: str  # "context" | "added" | "removed"
    content: str


class DiffHunk(BaseModel):
    old_start: int
    old_count: int
    new_start: int
    new_count: int
    lines: list[DiffHunkLine]


class DocumentVersionWithContent(DocumentVersionResponse):
    content: str


class DocumentDiffResponse(BaseModel):
    v1: DocumentVersionWithContent
    v2: DocumentVersionWithContent
    hunks: list[DiffHunk]
