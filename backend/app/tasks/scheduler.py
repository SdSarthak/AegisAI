"""
Background scheduler — periodic compliance snapshots and reassessment reminders.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
<<<<<<< HEAD
from datetime import datetime, timedelta

from app.core.database import SessionLocal
from app.models.compliance_snapshot import ComplianceSnapshot
from app.models.ai_system import AISystem
from app.models.notification import Notification, NotificationType

=======
from app.core.database import SessionLocal
from app.models.ai_system import AISystem
from app.models.notification import Notification, NotificationType

>>>>>>> 4d98067 (Implement reassessment reminder notifications)
scheduler = AsyncIOScheduler()


@scheduler.scheduled_job("cron", hour=2, minute=0)
def snapshot_compliance_scores():
<<<<<<< HEAD
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
=======
    """Daily job: capture a ComplianceSnapshot for every AI system."""
    pass
>>>>>>> 4d98067 (Implement reassessment reminder notifications)


@scheduler.scheduled_job("cron", hour=3, minute=0)
def send_reassessment_reminders():
<<<<<<< HEAD
    """
    Daily job: notify users when reassessment reminders
    are due.

    NOTE:
    RiskAssessment model dependency is currently unavailable
    in the repository. Full reminder integration will be
    completed once dependent issues/models are merged.
    """
=======
    """Daily job: notify users when reassessment is due."""
>>>>>>> 4d98067 (Implement reassessment reminder notifications)

    db = SessionLocal()

    try:
<<<<<<< HEAD
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
=======
        systems = db.query(AISystem).all()

        for system in systems:
            existing_notification = (
                db.query(Notification)
                .filter(
                    Notification.user_id == system.owner_id,
                    Notification.title == "Reassessment Due",
                )
                .first()
            )

            if not existing_notification:
                notification = Notification(
                    user_id=system.owner_id,
                    title="Reassessment Due",
                    message=f"AI System '{system.name}' may require reassessment soon.",
                    notification_type=NotificationType.REASSESSMENT_DUE,
                )

                db.add(notification)
>>>>>>> 4d98067 (Implement reassessment reminder notifications)

        db.commit()

    finally:
        db.close()