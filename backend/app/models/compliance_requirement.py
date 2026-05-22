from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base

class RequirementStatus(str, enum.Enum):
    TODO = "todo"
    IN_PROGRESS = "in_progress"
    DONE = "done"

class ComplianceRequirement(Base):
    __tablename__ = "compliance_requirements"

    id = Column(Integer, primary_key=True, index=True)
    ai_system_id = Column(Integer, ForeignKey("ai_systems.id"), nullable=False)
    requirement_id = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    article_reference = Column(String(100), nullable=True)
    status = Column(Enum(RequirementStatus), default=RequirementStatus.TODO)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationship
    ai_system = relationship("AISystem", back_populates="requirements")