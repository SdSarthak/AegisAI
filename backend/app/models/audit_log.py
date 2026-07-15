"""Audit log models for governance-sensitive events.

Changed: Added RAGAuditLog alongside the existing AISystemAuditLog.
Why: RAG guard, chunk filtering, and grounding events need durable audit records.
Addresses: Prompt-injection traceability without storing raw user questions or PII.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from datetime import datetime
import enum
import uuid

from sqlalchemy import (
    Column,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    event,
)
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
    ai_system_id = Column(Integer, ForeignKey("ai_systems.id", ondelete="CASCADE"), nullable=False)
    # SET NULL rather than CASCADE: this is a compliance audit trail and must
    # survive deletion of the user who made the change.
    changed_by_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # JSON dicts of {field: value} before and after the change
    old_values = Column(JSON, default=dict)
    new_values = Column(JSON, default=dict)

    changed_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    ai_system = relationship("AISystem", back_populates="audit_logs")
    changed_by = relationship("User")


class RAGAuditLog(Base):
    """Audit record for RAG prompt guard, chunk scan, and grounding events."""

    __tablename__ = "rag_audit_logs"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    # SET NULL rather than CASCADE: this is a compliance audit trail and must
    # survive deletion of the user it was recorded for.
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True, index=True)
    event_type = Column(String(64), nullable=False, index=True)
    question_hash = Column(String(64), nullable=False, index=True)
    decision = Column(String(16), nullable=False)
    reasoning = Column(String(1000), nullable=True)
    changes_summary = Column(String(1000), nullable=True)
    chunks_total = Column(Integer, nullable=True)
    chunks_dropped = Column(Integer, nullable=True)
    grounding_score = Column(Float, nullable=True)
    ip_address = Column(String(64), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    user = relationship("User")


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
