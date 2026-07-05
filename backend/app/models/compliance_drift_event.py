"""
ComplianceDriftEvent model — records when scheduled re-classification
detects a change in an AI system's risk level, compliance status, or
classifier version.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import enum
from datetime import datetime

from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import relationship

from app.core.database import Base


class DriftType(str, enum.Enum):
    RISK_CHANGE = "risk_change"
    STATUS_CHANGE = "status_change"
    CLASSIFIER_VERSION_CHANGE = "classifier_version_change"
    MIXED = "mixed"


class ComplianceDriftEvent(Base):
    """One row per detected drift on an AI system."""

    __tablename__ = "compliance_drift_events"

    id = Column(Integer, primary_key=True, index=True)
    ai_system_id = Column(
        Integer, ForeignKey("ai_systems.id", ondelete="CASCADE"), nullable=False
    )

    detected_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    drift_type = Column(Enum(DriftType), nullable=False)

    # Before / after snapshot — strings so removed enum values don't crash
    # the read path (forward-compat with future risk levels).
    previous_risk_level = Column(String(50), nullable=True)
    new_risk_level = Column(String(50), nullable=True)
    previous_status = Column(String(50), nullable=True)
    new_status = Column(String(50), nullable=True)
    classifier_version = Column(String(32), nullable=False)

    # Delivery tracking
    notified_in_app = Column(Boolean, default=False, nullable=False)
    webhook_delivered_at = Column(DateTime, nullable=True)
    webhook_response_code = Column(Integer, nullable=True)
    webhook_error = Column(Text, nullable=True)

    ai_system = relationship("AISystem", back_populates="drift_events")

    __table_args__ = (
        Index("ix_drift_events_system_detected", "ai_system_id", "detected_at"),
    )