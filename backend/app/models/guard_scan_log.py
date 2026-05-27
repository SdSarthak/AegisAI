"""
GuardScanLog model — records every prompt scan decision made by the LLM Guard.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from datetime import datetime

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, JSON, Boolean
from sqlalchemy.orm import relationship

from app.core.database import Base


class GuardScanLog(Base):
    __tablename__ = "guard_scan_logs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)

    raw_prompt = Column(String, nullable=True)
    prompt_hash = Column(String(64), nullable=False)  # SHA-256 hex digest
    decision = Column(String(16), nullable=False)      # allow | sanitize | block
    confidence = Column(Float, nullable=False)
    matched_patterns = Column(JSON, default=list)

    # New fields for audit/statistics
    detection_type = Column(String(16), default="none", nullable=False)
    regex_flag = Column(Boolean, default=False, nullable=False)
    regex_score = Column(Float, default=0.0, nullable=False)
    intent = Column(String(32), default="benign", nullable=False)
    ml_confidence = Column(Float, default=0.0, nullable=False)
    combined_score = Column(Float, default=0.0, nullable=False)
    prompt_length = Column(Integer, nullable=True)
    ip_address = Column(String(45), nullable=True)
    scanned_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    user = relationship("User")
