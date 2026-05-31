"""GuardAuditLog model — stores privacy-safe Guard audit history.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

Prompts are stored as SHA-256 hashes only — never raw text — to protect user privacy.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from app.core.database import Base


class GuardAuditLog(Base):
    __tablename__ = "guard_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    prompt_hash = Column(String(64), nullable=False, index=True)
    decision = Column(String(16), nullable=False)
    threat_type = Column(String(32), nullable=False, default="unknown")
    confidence_score = Column(Float, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User")
