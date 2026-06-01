import enum
from datetime import datetime

from sqlalchemy import Column, DateTime, Enum, ForeignKey, Integer, String

from app.core.database import Base


class SourceType(str, enum.Enum):
    UPLOADED = "UPLOADED"
    PRE_LOADED = "PRE_LOADED"


class IngestedDocument(Base):
    __tablename__ = "ingested_documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(500), nullable=False)
    source_type = Column(
        Enum(SourceType),
        default=SourceType.UPLOADED,
        nullable=False,
    )
    regulation_name = Column(String(200), nullable=True)
    file_hash = Column(String(64), nullable=False, index=True)
    file_size_bytes = Column(Integer, default=0, nullable=False)
    chunk_count = Column(Integer, default=0, nullable=False)
    uploaded_by_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
