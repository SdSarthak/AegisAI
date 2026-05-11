from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class DocumentType(str, enum.Enum):
    TECHNICAL_DOCUMENTATION = "technical_documentation"
    RISK_ASSESSMENT = "risk_assessment"
    CONFORMITY_DECLARATION = "conformity_declaration"
    DATA_GOVERNANCE = "data_governance"
    TRANSPARENCY_NOTICE = "transparency_notice"
    HUMAN_OVERSIGHT_PLAN = "human_oversight_plan"
    INCIDENT_REPORT = "incident_report"


class DocumentStatus(str, enum.Enum):
    DRAFT = "draft"
    GENERATED = "generated"
    REVIEWED = "reviewed"
    APPROVED = "approved"
    ARCHIVED = "archived"


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    ai_system_id = Column(Integer, ForeignKey("ai_systems.id"), nullable=True)

    # Document info
    title = Column(String(255), nullable=False)
    document_type = Column(Enum(DocumentType), nullable=False)
    status = Column(Enum(DocumentStatus), default=DocumentStatus.DRAFT)

    # Content
    content = Column(Text)  # Markdown or HTML content
    file_path = Column(String(500))  # Path to generated PDF

    # Versioning
    version = Column(String(20), default="1.0")

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    owner = relationship("User", back_populates="documents")
    ai_system = relationship("AISystem", back_populates="documents")
