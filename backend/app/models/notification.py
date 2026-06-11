"""Persist user-facing in-app notifications for backend events.

The model stores the notification content, read state, and optional
resource links used by guard, compliance, and webhook flows.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import enum
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from app.core.database import Base


class NotificationType(str, enum.Enum):
    SYSTEM_CLASSIFIED = "system_classified"
    DOCUMENT_GENERATED = "document_generated"
    GUARD_BLOCK = "guard_block"
    COMPLIANCE_DRIFT = "compliance_drift"
    REASSESSMENT_DUE = "reassessment_due"


class Notification(Base):
    __tablename__ = "notifications"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    notification_type = Column(String(100), nullable=False)  # NotificationType value
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False)

    # Optional link back to the relevant resource
    resource_type = Column(String(100), nullable=True)  # e.g. "ai_system", "document"
    resource_id = Column(Integer, nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="notifications")
