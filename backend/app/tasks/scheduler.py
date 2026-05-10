"""
Background scheduler — periodic compliance snapshots and reassessment reminders.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.models.compliance_snapshot import ComplianceSnapshot
from app.models.ai_system import AISystem
from app.models.notification import Notification, NotificationType

scheduler = AsyncIOScheduler()


@scheduler.scheduled_job("cron", hour=2, minute=0)
def snapshot_compliance_scores():
    """
    Daily job: capture a ComplianceSnapshot for every AI system.
    """

    db = SessionLocal()

    try:
        systems = db.query(AISystem).all()

        for system in systems:
            snapshot = ComplianceSnapshot(
                ai_system_id=system.id,
                compliance_score=system.compliance_score,
                compliance_status=system.compliance_status,
                risk_level=system.risk_level,
            )

            db.add(snapshot)

        db.commit()

    finally:
        db.close()


@scheduler.scheduled_job("cron", hour=3, minute=0)
def send_reassessment_reminders():
    """
    Daily job: notify users when reassessment reminders
    are due.

    NOTE:
    RiskAssessment model dependency is currently unavailable
    in the repository. Full reminder integration will be
    completed once dependent issues/models are merged.
    """

    db = SessionLocal()

    try:
        current_time = datetime.utcnow()

        # Prevent duplicate notifications within last 7 days
        existing_notification = (
            db.query(Notification)
            .filter(
                Notification.notification_type
                == NotificationType.REASSESSMENT_DUE
            )
            .filter(
                Notification.created_at
                >= current_time - timedelta(days=7)
            )
            .first()
        )

        if not existing_notification:
            # Placeholder for future RiskAssessment integration
            pass

        db.commit()

    finally:
        db.close()