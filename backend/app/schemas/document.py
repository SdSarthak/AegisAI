from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.models.document import DocumentType, DocumentStatus


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

class DocumentResponse(BaseModel):
    id: int
    title: str
    document_type: DocumentType
    status: DocumentStatus
    content: Optional[str]
    file_path: Optional[str]
    version: str
    ai_system_id: Optional[int]
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentGenerateRequest(BaseModel):
    """Request to generate a compliance document."""
    document_type: DocumentType
    ai_system_id: int
    include_recommendations: bool = True
