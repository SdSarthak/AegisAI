"""
APScheduler setup: runs the compliance drift monitor on a cron schedule.

Started from the FastAPI lifespan handler in ``app/main.py``. Stops cleanly
on shutdown so uvicorn's reload doesn't leak schedulers.

Configuration via env var ``COMPLIANCE_MONITOR_CRON``. Default ``0 2 * * *``
(02:00 daily). Set to empty string to disable the scheduled job (the
``POST /admin/compliance/scan`` endpoint still works for manual runs).

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.core.config import settings
from app.modules.compliance.monitor import run_drift_scan

logger = logging.getLogger("aegisai.scheduler")

_scheduler: Optional[AsyncIOScheduler] = None


def start_scheduler() -> Optional[AsyncIOScheduler]:
    """Idempotent. Returns the scheduler instance, or ``None`` if disabled."""
    global _scheduler
    if _scheduler is not None:
        return _scheduler

    cron_expr = getattr(settings, "COMPLIANCE_MONITOR_CRON", "0 2 * * *").strip()
    if not cron_expr:
        logger.info("scheduler.disabled_by_config")
        return None

    try:
        trigger = CronTrigger.from_crontab(cron_expr)
    except ValueError:
        logger.exception("scheduler.invalid_cron", extra={"cron": cron_expr})
        return None

    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        run_drift_scan,
        trigger=trigger,
        id="compliance_drift_scan",
        name="Compliance drift scan",
        misfire_grace_time=600,  # accept up to 10 min late if the loop was busy
        coalesce=True,  # if multiple fires queued (e.g. after a long pause), run once
        max_instances=1,
    )
    scheduler.start()
    _scheduler = scheduler
    logger.info("scheduler.started", extra={"cron": cron_expr})
    return scheduler


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler is not None:
        _scheduler.shutdown(wait=False)
        _scheduler = None
        logger.info("scheduler.stopped")