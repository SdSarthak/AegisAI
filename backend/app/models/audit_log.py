"""Audit log entries for changes made to AI system records.

Each row stores the before/after values for tracked fields so compliance and
administrative changes can be reviewed later without diffing the source row.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import enum
from datetime import datetime

from sqlalchemy import JSON, Column, DateTime, ForeignKey, Integer, event
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


def _json_safe_value(value):
    if isinstance(value, enum.Enum):
        return value.value
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple, set)):
        return [_json_safe_value(item) for item in value]
    return value


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
    ai_system = relationship("AISystem", back_populates="audit_logs")
    changed_by = relationship("User")


@event.listens_for(AISystem, "after_update")
def after_ai_system_update(mapper, connection, target):
    old_values = {}
    new_values = {}

    for field in TRACKED_FIELDS:
        history = get_history(target, field)

        if history.has_changes():
            old_values[field] = _json_safe_value(
                history.deleted[0] if history.deleted else None
            )
            new_values[field] = _json_safe_value(
                history.added[0] if history.added else getattr(target, field)
            )
    changed_by_id = getattr(target, "_changed_by_id", None)
    if old_values and changed_by_id:
        connection.execute(
            AISystemAuditLog.__table__.insert().values(
                ai_system_id=target.id,
                changed_by_id=changed_by_id,
                old_values=_json_safe_value(old_values),
                new_values=_json_safe_value(new_values),
                changed_at=datetime.utcnow(),
            )
        )
