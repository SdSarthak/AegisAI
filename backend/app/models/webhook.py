"""
WebhookConfig model — user-configured endpoints for event delivery.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

TODO for contributors (good first issue):
  - This model is complete. Register it in app/models/__init__.py and
    create an Alembic migration.
  - Acceptance criteria: `alembic revision --autogenerate` produces a
    migration that creates the `webhook_configs` table.
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
