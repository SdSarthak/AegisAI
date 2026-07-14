"""
Background scheduler — periodic compliance snapshots and reassessment reminders.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.ai_system import AISystem, RiskAssessment
from app.models.compliance_snapshot import ComplianceSnapshot
from app.models.notification import Notification, NotificationType
from app.models.user import User

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()

_BATCH_SIZE = 100


def _get_user_ids(db: Session) -> list[int]:
    """Return all user IDs in the system for per-user processing."""
    return [u[0] for u in db.query(User.id).all()]


def snapshot_compliance_scores():
    """Daily snapshot of compliance scores for historical trend analysis."""
    db: Session = SessionLocal()
    total_systems = 0
    processed_users = 0

    try:
        user_ids = _get_user_ids(db)

        for user_id in user_ids:
            try:
                systems = (
                    db.query(AISystem)
                    .filter(AISystem.owner_id == user_id)
                    .yield_per(_BATCH_SIZE)
                )

                user_count = 0
                for system in systems:
                    if system.compliance_score is None:
                        continue
                    snapshot = ComplianceSnapshot(
                        ai_system_id=system.id,
                        compliance_score=system.compliance_score,
                        compliance_status=(
                            system.compliance_status.value
                            if system.compliance_status
                            else "not_started"
                        ),
                        risk_level=(
                            system.risk_level.value
                            if system.risk_level
                            else None
                        ),
                    )
                    db.add(snapshot)
                    user_count += 1

                if user_count:
                    db.commit()
                    total_systems += user_count
                    processed_users += 1
                    logger.info(
                        "Compliance snapshot created for %d systems for user %d",
                        user_count,
                        user_id,
                    )
            except Exception:
                db.rollback()
                logger.exception(
                    "Failed to create compliance snapshot for user %d", user_id
                )

        logger.info(
            "Compliance snapshot completed: %d systems across %d users",
            total_systems,
            processed_users,
        )
    except Exception:
        db.rollback()
        logger.exception("Failed to create compliance snapshot")
    finally:
        db.close()


def send_reassessment_reminders():
    """Send notifications for risk assessments expiring within 30 days."""
    db: Session = SessionLocal()
    total_reminders = 0
    processed_users = 0

    try:
        user_ids = _get_user_ids(db)

        for user_id in user_ids:
            try:
                thirty_days = datetime.utcnow() + timedelta(days=30)
                expiring = (
                    db.query(RiskAssessment)
                    .filter(
                        RiskAssessment.valid_until <= thirty_days,
                        RiskAssessment.valid_until > datetime.utcnow(),
                    )
                    .join(AISystem, RiskAssessment.ai_system_id == AISystem.id)
                    .filter(AISystem.owner_id == user_id)
                    .yield_per(_BATCH_SIZE)
                )

                user_reminders = 0
                for assessment in expiring:
                    system = (
                        db.query(AISystem)
                        .filter(AISystem.id == assessment.ai_system_id)
                        .first()
                    )
                    if not system:
                        continue

                    notification = Notification(
                        user_id=system.owner_id,
                        notification_type=NotificationType.REASSESSMENT_DUE.value,
                        title="Risk Assessment Expiring Soon",
                        message=(
                            f"Risk assessment for AI system '{system.name}' "
                            f"expires on {assessment.valid_until.date()}. "
                            f"Please schedule a reassessment."
                        ),
                        resource_type="risk_assessment",
                        resource_id=assessment.id,
                    )
                    db.add(notification)
                    user_reminders += 1

                if user_reminders:
                    db.commit()
                    total_reminders += user_reminders
                    processed_users += 1
                    logger.info(
                        "Sent %d reassessment reminders for user %d",
                        user_reminders,
                        user_id,
                    )
            except Exception:
                db.rollback()
                logger.exception(
                    "Failed to send reassessment reminders for user %d", user_id
                )

        if total_reminders:
            logger.info(
                "Reassessment reminders completed: %d reminders across %d users",
                total_reminders,
                processed_users,
            )
    except Exception:
        db.rollback()
        logger.exception("Failed to send reassessment reminders")
    finally:
        db.close()
