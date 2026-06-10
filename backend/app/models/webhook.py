"""Store webhook delivery settings for user-configured endpoints.

The model tracks the target URL, signing secret, enabled state, and event
subscriptions so background jobs can deliver notifications consistently.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from sqlalchemy import Column, Integer, String, Boolean, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.core.database import Base


class WebhookConfig(Base):
    __tablename__ = "webhook_configs"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    url = Column(String(1000), nullable=False)
    secret = Column(String(255), nullable=True)  # HMAC signing secret
    is_active = Column(Boolean, default=True)

    # List of event types to deliver, e.g. ["guard_block", "compliance_drift"]
    events = Column(JSON, default=list)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="webhook_configs")
