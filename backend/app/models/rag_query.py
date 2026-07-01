from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from datetime import datetime
from app.core.database import Base


class RagQuery(Base):
    __tablename__ = "rag_queries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question_hash = Column(String(64), nullable=False)
    question_length = Column(Integer, nullable=True)
    answer_hash = Column(String(64), nullable=True)
    answer_length = Column(Integer, nullable=True)
    source_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
