"""
Background scheduler — periodic compliance snapshots and reassessment reminders.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import logging
from datetime import datetime, timedelta, timezone

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.ai_system import AISystem, RiskAssessment
from app.models.compliance_snapshot import ComplianceSnapshot
from app.models.notification import Notification, NotificationType

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def snapshot_compliance_scores():
    """Daily snapshot of compliance scores for historical trend analysis."""
    db: Session = SessionLocal()
    try:
        systems = db.query(AISystem).all()
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
        db.commit()
        logger.info("Compliance snapshot created for %d systems", len(systems))
    except Exception:
        db.rollback()
        logger.exception("Failed to create compliance snapshot")
    finally:
        db.close()


def send_reassessment_reminders():
    """Send notifications for risk assessments expiring within 30 days."""
    db: Session = SessionLocal()
    try:
        thirty_days = datetime.now(timezone.utc) + timedelta(days=30)
        expiring = (
            db.query(RiskAssessment)
            .filter(
                RiskAssessment.valid_until <= thirty_days,
                RiskAssessment.valid_until > datetime.now(timezone.utc),
            )
            .all()
        )

        reminders_sent = 0
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
            reminders_sent += 1

        db.commit()
        if reminders_sent:
            logger.info("Sent %d reassessment reminders", reminders_sent)
    except Exception:
        db.rollback()
        logger.exception("Failed to send reassessment reminders")
    finally:
        db.close()
