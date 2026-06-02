"""
Background scheduler — periodic compliance snapshots and reassessment reminders.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

This module implements a lightweight daily scheduler to capture compliance
snapshots for AI systems and notify their owners when risk assessments are
coming due.
"""

import logging
from datetime import datetime, timedelta

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from app.core.database import SessionLocal
from app.models.ai_system import AISystem, RiskAssessment
from app.models.compliance_snapshot import ComplianceSnapshot
from app.models.notification import Notification, NotificationType

logger = logging.getLogger("aegisai.scheduler")

scheduler = AsyncIOScheduler(job_defaults={"coalesce": False, "max_instances": 1})


@scheduler.scheduled_job("cron", hour=2, minute=0)
def snapshot_compliance_scores():
    """Daily job: capture a ComplianceSnapshot for every AI system."""
    db = SessionLocal()
    try:
        today = datetime.utcnow().date()
        day_start = datetime(today.year, today.month, today.day)
        next_day = day_start + timedelta(days=1)

        systems = db.query(AISystem).all()
        for system in systems:
            if system is None:
                continue

            existing_snapshot = (
                db.query(ComplianceSnapshot)
                .filter(
                    ComplianceSnapshot.ai_system_id == system.id,
                    ComplianceSnapshot.snapshotted_at >= day_start,
                    ComplianceSnapshot.snapshotted_at < next_day,
                )
                .first()
            )
            if existing_snapshot:
                continue

            snapshot = ComplianceSnapshot(
                ai_system_id=system.id,
                compliance_score=int(system.compliance_score or 0),
                compliance_status=(system.compliance_status.value
                                   if system.compliance_status else "not_started"),
                risk_level=(system.risk_level.value if system.risk_level else None),
                snapshotted_at=datetime.utcnow(),
            )
            db.add(snapshot)

        db.commit()
        logger.info("Compliance snapshot job completed for %d systems", len(systems))
    except Exception:
        db.rollback()
        logger.exception("Failed to snapshot compliance scores")
    finally:
        db.close()


@scheduler.scheduled_job("cron", hour=3, minute=0)
def send_reassessment_reminders():
    """Daily job: notify users when a risk assessment is expiring within 30 days."""
    db = SessionLocal()
    try:
        now = datetime.utcnow()
        due_by = now + timedelta(days=30)
        recent_threshold = now - timedelta(days=7)

        assessments = (
            db.query(RiskAssessment)
            .join(AISystem, RiskAssessment.ai_system_id == AISystem.id)
            .filter(
                RiskAssessment.valid_until >= now,
                RiskAssessment.valid_until <= due_by,
            )
            .all()
        )

        created = 0
        for assessment in assessments:
            system = assessment.ai_system
            if not system or not system.owner:
                continue

            existing_notification = (
                db.query(Notification)
                .filter(
                    Notification.user_id == system.owner.id,
                    Notification.notification_type == NotificationType.REASSESSMENT_DUE.value,
                    Notification.resource_type == "ai_system",
                    Notification.resource_id == system.id,
                    Notification.created_at >= recent_threshold,
                )
                .first()
            )

            if existing_notification:
                continue

            notification = Notification(
                user_id=system.owner.id,
                notification_type=NotificationType.REASSESSMENT_DUE.value,
                title="Risk reassessment due soon",
                message=(
                    f"Risk assessment for AI system '{system.name}' is expiring on "
                    f"{assessment.valid_until.date()}. Please schedule a reassessment."
                ),
                resource_type="ai_system",
                resource_id=system.id,
            )
            db.add(notification)
            created += 1

        db.commit()
        logger.info("Reassessment reminder job created %d notifications", created)
    except Exception:
        db.rollback()
        logger.exception("Failed to send reassessment reminders")
    finally:
        db.close()


def start_scheduler():
    if not scheduler.running:
        scheduler.start()
        logger.info("APScheduler started")


def shutdown_scheduler():
    if scheduler.running:
        scheduler.shutdown(wait=False)
        logger.info("APScheduler shutdown")
