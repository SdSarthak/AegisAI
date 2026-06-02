from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class GuardAuditLog(Base):
    __tablename__ = "guard_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    prompt_hash = Column(String(64), nullable=False)
    decision = Column(String(16), nullable=False)
    threat_type = Column(String(32), default="none", nullable=False)
    confidence_score = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User")
