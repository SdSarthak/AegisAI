"""
Background scheduler — periodic compliance snapshots and reassessment reminders.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import logging
from apscheduler.schedulers.background import BackgroundScheduler
from app.core.database import SessionLocal
from app.models.compliance_snapshot import ComplianceSnapshot
from app.models.ai_system import AISystem

logger = logging.getLogger("aegisai.scheduler")

scheduler = BackgroundScheduler()


@scheduler.scheduled_job("cron", hour=2, minute=0)
def snapshot_compliance_scores():
    """Daily job: capture a ComplianceSnapshot for every AI system."""
    db = SessionLocal()
    try:
        systems = db.query(AISystem).all()
        for system in systems:
            snapshot = ComplianceSnapshot(
                ai_system_id=system.id,
                compliance_score=system.compliance_score,
                compliance_status=system.compliance_status.value,
                risk_level=system.risk_level.value if system.risk_level else None,
            )
            db.add(snapshot)
        db.commit()
        logger.info(
            "ComplianceSnapshot captured for %d AI systems.", len(systems)
        )
    except Exception:
        logger.exception("Failed to capture compliance snapshots")
        db.rollback()
    finally:
        db.close()