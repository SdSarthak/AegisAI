from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime

from app.core.database import Base


class ApiKey(Base):
    __tablename__ = "api_keys"

    id = Column(Integer, primary_key=True, index=True)

    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    name = Column(String(255), nullable=False)

    key_hash = Column(String(255), nullable=False, unique=True, index=True)

    revoked = Column(Boolean, default=False)

    created_at = Column(DateTime, default=datetime.utcnow)

    revoked_at = Column(DateTime, nullable=True)

    user = relationship("User")