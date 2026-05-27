"""
Background scheduler — periodic compliance snapshots and reassessment reminders.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

TODO for contributors (high priority):
  - Install APScheduler: add `apscheduler>=3.10` to backend/requirements.txt.
  - Implement `snapshot_compliance_scores()`:
      * Open a DB session.
      * Query all active AISystem rows.
      * For each system, insert a ComplianceSnapshot row with the current
        compliance_score, compliance_status, and risk_level.
  - Implement `send_reassessment_reminders()`:
      * Query RiskAssessment rows where valid_until is within 30 days
        from today and the system owner has not been notified recently.
      * Create a Notification row of type REASSESSMENT_DUE for the owner.
  - Wire both jobs into the APScheduler instance below and start the
    scheduler when the FastAPI app starts (use app lifespan or startup event).
  - Acceptance criteria: after the scheduler runs, ComplianceSnapshot rows
    appear in the DB and REASSESSMENT_DUE notifications appear for affected users.
"""

# TODO (high priority): uncomment and implement once APScheduler is installed
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.database import SessionLocal
from app.models.compliance_snapshot import ComplianceSnapshot
from app.models.ai_system import AISystem, RiskAssessment
from app.models.notification import Notification, NotificationType
def create_notification(
    db,
    user_id,
    notification_type,
    title,
    message,
    resource_type=None,
    resource_id=None,
):
    notification = Notification(
        user_id=user_id,
        notification_type=notification_type,
        title=title,
        message=message,
        resource_type=resource_type,
        resource_id=resource_id,
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification


from datetime import datetime, timedelta

scheduler = BackgroundScheduler()


@scheduler.scheduled_job("cron", hour=3, minute=0)
def send_reassessment_reminders():
    """Daily job: notify users when a risk assessment is expiring within 30 days."""

    db = SessionLocal()

    try:
        now = datetime.utcnow()
        cutoff = now + timedelta(days=30)
        seven_days_ago = now - timedelta(days=7)

        due_assessments = (
            db.query(RiskAssessment)
            .filter(RiskAssessment.valid_until <= cutoff)
            .filter(RiskAssessment.valid_until >= now)
            .all()
        )

        for assessment in due_assessments:
            system = assessment.ai_system

            existing_notification = (
                db.query(Notification)
                .filter(Notification.user_id == system.owner_id)
                .filter(
                    Notification.notification_type
                    == NotificationType.REASSESSMENT_DUE.value
                )
                .filter(Notification.resource_id == system.id)
                .filter(Notification.created_at >= seven_days_ago)
                .first()
            )

            if existing_notification:
                continue

            create_notification(
                db=db,
                user_id=system.owner_id,
                notification_type=NotificationType.REASSESSMENT_DUE.value,
                title="Risk assessment due soon",
                message=(
                    f"{system.name} requires re-assessment by "
                    f"{assessment.valid_until.date()}"
                ),
                resource_type="ai_system",
                resource_id=system.id,
            )

    finally:
        db.close()


# @scheduler.scheduled_job("cron", hour=3, minute=0)   # runs daily at 03:00 UTC
# def send_reassessment_reminders():
#     """Daily job: notify users when a risk assessment is expiring within 30 days."""
#     # TODO: implement
#     pass
