"""
Email notification tasks for AegisAI compliance deadline alerts.
Integrates with the existing APScheduler setup in scheduler.py.
"""

import logging
from datetime import datetime, timedelta, timezone

from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.core.email import (
    build_deadline_alert_email,
    build_reassessment_email,
    send_email,
)
from app.models.ai_system import AISystem, RiskAssessment
from app.models.user import User

logger = logging.getLogger(__name__)


def send_compliance_deadline_email_alerts() -> None:
    """
    Send email alerts for AI systems with compliance deadlines
    within the next 7, 14, or 30 days.
    """
    db: Session = SessionLocal()
    try:
        now = datetime.now(timezone.utc)
        alert_thresholds = [7, 14, 30]

        systems = db.query(AISystem).filter(
            AISystem.next_review_date.isnot(None)
        ).all()

        emails_sent = 0
        for system in systems:
            if not system.next_review_date:
                continue

            days_remaining = (system.next_review_date - now).days

            if days_remaining not in alert_thresholds:
                continue

            owner = db.query(User).filter(User.id == system.owner_id).first()
            if not owner or not owner.email:
                continue

            email_content = build_deadline_alert_email(
                system_name=system.name,
                deadline_date=system.next_review_date.strftime("%B %d, %Y"),
                days_remaining=days_remaining,
            )

            success = send_email(
                to_email=owner.email,
                subject=email_content["subject"],
                html_body=email_content["html_body"],
                text_body=email_content["text_body"],
            )

            if success:
                emails_sent += 1
                logger.info(
                    "Compliance deadline alert sent to %s for system '%s' (%d days remaining)",
                    owner.email,
                    system.name,
                    days_remaining,
                )

        logger.info("Sent %d compliance deadline email alerts", emails_sent)

    except Exception:
        logger.exception("Failed to send compliance deadline email alerts")
    finally:
        db.close()


def send_reassessment_email_reminders() -> None:
    """
    Send email reminders for risk assessments expiring within 30 days.
    Complements the existing in-app notification in scheduler.py.
    """
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

        emails_sent = 0
        for assessment in expiring:
            system = (
                db.query(AISystem)
                .filter(AISystem.id == assessment.ai_system_id)
                .first()
            )
            if not system:
                continue

            owner = db.query(User).filter(User.id == system.owner_id).first()
            if not owner or not owner.email:
                continue

            email_content = build_reassessment_email(
                system_name=system.name,
                expiry_date=assessment.valid_until.strftime("%B %d, %Y"),
            )

            success = send_email(
                to_email=owner.email,
                subject=email_content["subject"],
                html_body=email_content["html_body"],
                text_body=email_content["text_body"],
            )

            if success:
                emails_sent += 1
                logger.info(
                    "Reassessment email reminder sent to %s for system '%s'",
                    owner.email,
                    system.name,
                )

        logger.info("Sent %d reassessment email reminders", emails_sent)

    except Exception:
        logger.exception("Failed to send reassessment email reminders")
    finally:
        db.close()
        