from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Text

from app.core.database import Base


class RagQuery(Base):
    __tablename__ = "rag_queries"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer_summary = Column(String(200), nullable=True)
    source_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
