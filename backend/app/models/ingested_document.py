"""Model for tracking documents ingested into the RAG knowledge base."""

import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String
from sqlalchemy.orm import relationship

from app.core.database import Base


class SourceType(str, enum.Enum):
    """How a document entered the knowledge base."""

    UPLOADED = "uploaded"
    PRE_LOADED = "pre_loaded"


class IngestedDocument(Base):
    """Registry row for every PDF ingested into the FAISS vector index.

    Attributes:
        filename: Original name of the uploaded/downloaded PDF.
        source_type: ``uploaded`` (user upload) or ``pre_loaded`` (bootstrap).
        regulation_name: Human-readable label, e.g. "EU AI Act", "GDPR".
        file_hash: SHA-256 hex digest used for duplicate detection.
        file_size_bytes: Size of the raw PDF in bytes.
        chunk_count: Number of text chunks created by the splitter.
        uploaded_by_id: FK to the user who uploaded (NULL for pre-loaded).
        created_at: Timestamp of ingestion.
    """

    __tablename__ = "ingested_documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)
    source_type = Column(
        Enum(SourceType), nullable=False, default=SourceType.UPLOADED,
    )
    regulation_name = Column(String(200), nullable=True)
    file_hash = Column(String(64), nullable=False, index=True)
    file_size_bytes = Column(Integer, nullable=False, default=0)
    chunk_count = Column(Integer, nullable=False, default=0)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    uploader = relationship("User", backref="ingested_documents", lazy="select")

    def __repr__(self) -> str:
        return (
            f"<IngestedDocument id={self.id} filename='{self.filename}' "
            f"source={self.source_type.value}>"
        )
