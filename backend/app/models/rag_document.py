from datetime import datetime

from sqlalchemy import Column, DateTime, Integer, String

from app.core.database import Base


class RAGDocument(Base):
    __tablename__ = "rag_documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String(255), nullable=False)
    original_filename = Column(String(255), nullable=False)
    storage_path = Column(String(1000), nullable=False)
    content_type = Column(String(255), nullable=True)
    file_size_bytes = Column(Integer, nullable=False, default=0)
    chunks_count = Column(Integer, nullable=False, default=0)
    uploaded_by_id = Column(Integer, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
