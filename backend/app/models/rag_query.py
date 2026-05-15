from sqlalchemy import Column, String, Integer, DateTime, Text, ForeignKey
from datetime import datetime
import uuid
from app.core.database import Base


class RagQuery(Base):
    __tablename__ = "rag_queries"

    id = Column(String(64), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id = Column(String(64), ForeignKey("users.id"), nullable=False)
    question = Column(Text, nullable=False)
    answer_summary = Column(String(200), nullable=True)
    source_count = Column(Integer, default=0)
    created_at = Column(DateTime, default=datetime.utcnow)
