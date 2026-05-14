"""
AISystemAuditLog model — records every field change on an AISystem row.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

TODO for contributors (help wanted):
  - Wire this model via a SQLAlchemy `event.listen` on AISystem's `after_update`
    event (see: https://docs.sqlalchemy.org/en/20/orm/events.html#sqlalchemy.orm.events.InstanceEvents.after_update).
  - Capture old_values and new_values by comparing the history of each column
    using `sqlalchemy.orm.attributes.get_history`.
  - Add a GET /api/v1/ai-systems/{id}/history endpoint that returns paginated
    log entries for a given system.
  - Acceptance criteria: updating a system's name via PATCH is reflected as a
    new row in ai_system_audit_logs with correct old/new values.
"""

from datetime import datetime

from sqlalchemy import Column, Integer, DateTime, ForeignKey, JSON, event
from sqlalchemy.orm import relationship
from sqlalchemy.orm.attributes import get_history

from app.core.database import Base
from app.models.ai_system import AISystem


TRACKED_FIELDS = [
    "name",
    "description",
    "use_case",
    "sector",
    "risk_level",
    "compliance_status",
    "compliance_score",
]


class AISystemAuditLog(Base):
    __tablename__ = "ai_system_audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    ai_system_id = Column(Integer, ForeignKey("ai_systems.id"), nullable=False)
    changed_by_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    # JSON dicts of {field: value} before and after the change
    old_values = Column(JSON, default=dict)
    new_values = Column(JSON, default=dict)

    changed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ai_system = relationship("AISystem")
    changed_by = relationship("User")


@event.listens_for(AISystem, "after_update")
def after_ai_system_update(mapper, connection, target):
    old_values = {}
    new_values = {}

    for field in TRACKED_FIELDS:
        history = get_history(target, field)

        if history.has_changes():
            old_values[field] = (
                history.deleted[0] if history.deleted else None
            )
            new_values[field] = (
                history.added[0] if history.added else None
            )

    if old_values:
        connection.execute(
            AISystemAuditLog.__table__.insert().values(
                ai_system_id=target.id,
                changed_by_id=target.owner_id,
                old_values=old_values,
                new_values=new_values,
                changed_at=datetime.utcnow(),
            )
        )
        