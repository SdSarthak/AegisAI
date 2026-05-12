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
# from apscheduler.schedulers.asyncio import AsyncIOScheduler
# from app.core.database import SessionLocal
# from app.models.compliance_snapshot import ComplianceSnapshot
# from app.models.ai_system import AISystem
# from app.models.risk_assessment import RiskAssessment
# from app.models.notification import Notification, NotificationType
# from datetime import datetime, timedelta

# scheduler = AsyncIOScheduler()


# @scheduler.scheduled_job("cron", hour=2, minute=0)   # runs daily at 02:00 UTC
# def snapshot_compliance_scores():
#     """Daily job: capture a ComplianceSnapshot for every AI system."""
#     # TODO: implement
#     pass


# @scheduler.scheduled_job("cron", hour=3, minute=0)   # runs daily at 03:00 UTC
# def send_reassessment_reminders():
#     """Daily job: notify users when a risk assessment is expiring within 30 days."""
#     # TODO: implement
#     pass
