"""
GuardScanLog model — records every prompt scan decision made by the LLM Guard.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

Prompts are stored as SHA-256 hashes only — never raw text — to protect user privacy.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship

from app.core.database import Base


class GuardScanLog(Base):
    __tablename__ = "guard_scan_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    prompt_hash = Column(String(64), nullable=False)  # SHA-256 hex digest
    decision = Column(String(16), nullable=False)      # allow | sanitize | block
    confidence = Column(Float, nullable=False)
    matched_patterns = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")
