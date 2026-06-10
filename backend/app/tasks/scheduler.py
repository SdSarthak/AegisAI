"""Background scheduler for compliance snapshots and reassessment reminders.

This module is intentionally left as a scaffold for the periodic jobs that
will capture daily compliance state and notify owners when reassessments are
approaching. The TODO block is part of the implementation plan and keeps the
required work visible to contributors.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
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
