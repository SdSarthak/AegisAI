from sqlalchemy import Column, Integer, String, DateTime, JSON
from datetime import datetime
import uuid
from app.core.database import Base


class RAGFeedback(Base):
    __tablename__ = "rag_feedback"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    question = Column(String(2000), nullable=True)
    answer = Column(String(4000), nullable=True)
    thumbs_up = Column(Integer, default=0)
    thumbs_down = Column(Integer, default=0)
    source_chunks = Column(JSON, default=list)
    created_at = Column(DateTime, default=datetime.utcnow)
