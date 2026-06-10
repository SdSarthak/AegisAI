"""Capture a point-in-time compliance snapshot for one AI system.

Each row stores the score, status, and risk level observed at a specific
moment so compliance trends can be tracked over time.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class ComplianceSnapshot(Base):
    __tablename__ = "compliance_snapshots"

    id = Column(Integer, primary_key=True, index=True)
    ai_system_id = Column(Integer, ForeignKey("ai_systems.id"), nullable=False)

    # Captured values at snapshot time
    compliance_score = Column(Integer, nullable=False)  # 0-100
    compliance_status = Column(String(50), nullable=False)  # ComplianceStatus value
    risk_level = Column(String(50), nullable=True)  # RiskLevel value

    snapshotted_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    ai_system = relationship("AISystem", back_populates="compliance_snapshots")
