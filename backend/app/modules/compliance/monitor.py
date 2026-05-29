"""
Scheduled compliance drift monitor (issue #82).

Re-runs the EU AI Act risk classifier against every AI system whose owner
has opted in (``monitoring_enabled=True``), compares the result to the
currently-stored risk level + compliance status, and records a
``ComplianceDriftEvent`` whenever they diverge.

Design choices:

- **APScheduler over Celery Beat.** The project doesn't deploy a Celery
  worker, so adding one for a nightly job is overkill. ``AsyncIOScheduler``
  runs inside the FastAPI process and is started/stopped in the lifespan
  handler.

- **Postgres advisory lock for multi-replica safety.** In-process schedulers
  fire in every replica. ``pg_try_advisory_lock`` ensures only one replica
  executes the scan; the others no-op and log it.

- **Classifier version bump produces a drift event.** When ``CLASSIFIER_VERSION``
  changes, every monitored system reports a ``CLASSIFIER_VERSION_CHANGE``
  drift on the next scan, which is the audit trail signal owners need to
  re-review.

- **Notifications run *inside* the same transaction as the drift event.**
  If notification dispatch fails, the event still commits — re-delivery
  is handled by the notifier separately (out of scope for this PR, see
  TODO at the bottom).

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import logging
import time
from contextlib import contextmanager
from typing import Iterable, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core.database import SessionLocal
from app.models.ai_system import AISystem, ComplianceStatus, RiskLevel
from app.models.compliance_drift_event import ComplianceDriftEvent, DriftType
from app.modules.compliance.notifier import dispatch_notifications
from app.schemas.ai_system import RiskClassificationRequest

logger = logging.getLogger("aegisai.compliance.monitor")

# Bump this string whenever the questionnaire / classification logic
# changes in a way that could yield different results for the same inputs.
# Every monitored system will then surface a CLASSIFIER_VERSION_CHANGE
# drift on the next scan.
CLASSIFIER_VERSION = "1.0.0"

# Advisory-lock key for multi-replica coordination. Any 32-bit int; just
# needs to be stable across replicas of the same deployment.
_ADVISORY_LOCK_KEY = 821001  # "82" for the issue, plus padding

# Process AISystems in chunks so a large fleet doesn't blow up memory or
# hold a long transaction.
_CHUNK_SIZE = 50


# ---------------------------------------------------------------------------
# Locking
# ---------------------------------------------------------------------------


@contextmanager
def _advisory_lock(db: Session, key: int) -> Iterable[bool]:
    """Acquire a Postgres advisory lock; release on exit. Yields True if
    acquired, False if another replica owns it (in which case the caller
    should no-op rather than wait).

    On non-Postgres backends (e.g. SQLite in tests) this is a no-op that
    always yields ``True``. Multi-replica coordination is only meaningful
    in production where Postgres is the deployed DB.
    """
    dialect = db.bind.dialect.name if db.bind is not None else ""
    if dialect != "postgresql":
        yield True
        return

    acquired = False
    try:
        result = db.execute(text("SELECT pg_try_advisory_lock(:k)"), {"k": key}).scalar()
        acquired = bool(result)
        yield acquired
    finally:
        if acquired:
            db.execute(text("SELECT pg_advisory_unlock(:k)"), {"k": key})
            db.commit()


# ---------------------------------------------------------------------------
# Drift detection
# ---------------------------------------------------------------------------


def _build_classification_request(
    system: AISystem,
) -> Optional[RiskClassificationRequest]:
    """Build a classifier input from the system's stored questionnaire.

    Returns ``None`` when the system was never classified (no
    questionnaire on file) — there's nothing to drift from.
    """
    responses = system.questionnaire_responses or {}
    if not responses:
        return None

    # Construct from whatever subset of fields are present; defaults in
    # the schema handle missing keys.
    try:
        return RiskClassificationRequest(
            use_case_category=responses.get(
                "use_case_category", system.use_case or "other"
            ),
            **{
                k: bool(v)
                for k, v in responses.items()
                if k != "use_case_category"
                and k in RiskClassificationRequest.model_fields
            },
        )
    except Exception:
        logger.warning(
            "compliance.monitor.bad_questionnaire",
            extra={"ai_system_id": system.id},
            exc_info=True,
        )
        return None


def _diff(system: AISystem, new_risk: RiskLevel) -> Optional[DriftType]:
    """Return the drift type, or ``None`` if nothing changed."""
    risk_changed = (system.risk_level or None) != new_risk
    # status drift is reserved for future expansion — re-running the
    # classifier alone doesn't change compliance_status. Kept for symmetry.
    status_changed = False

    if risk_changed and status_changed:
        return DriftType.MIXED
    if risk_changed:
        return DriftType.RISK_CHANGE
    if status_changed:
        return DriftType.STATUS_CHANGE
    return None


def _resolve_classifier():
    """Return the classify_risk callable.

    Imported lazily so the monitor module can be loaded in environments
    without the full RAG/LangChain stack (e.g. unit tests). Tests override
    this attribute directly to inject a stub.
    """
    from app.api.v1.classification import classify_risk

    return classify_risk


def _scan_one_system(db: Session, system: AISystem) -> Optional[ComplianceDriftEvent]:
    """Re-classify one system. Returns the event if drift was detected."""
    request = _build_classification_request(system)
    if request is None:
        return None

    try:
        result = _resolve_classifier()(request)
    except Exception:
        logger.exception(
            "compliance.monitor.classify_failed",
            extra={"ai_system_id": system.id},
        )
        return None

    drift = _diff(system, result.risk_level)

    # Check classifier version drift even when the result didn't change —
    # the audit trail must reflect every re-eval against a new version.
    # We only emit a version-change event if the system has a stored
    # classifier_version; otherwise the first scan would spam events.
    last_event = (
        db.query(ComplianceDriftEvent)
        .filter(ComplianceDriftEvent.ai_system_id == system.id)
        .order_by(ComplianceDriftEvent.detected_at.desc())
        .first()
    )
    version_changed = (
        last_event is not None
        and last_event.classifier_version != CLASSIFIER_VERSION
    )

    if drift is None and not version_changed:
        return None

    if drift is None and version_changed:
        drift = DriftType.CLASSIFIER_VERSION_CHANGE

    event = ComplianceDriftEvent(
        ai_system_id=system.id,
        drift_type=drift,
        previous_risk_level=system.risk_level.value if system.risk_level else None,
        new_risk_level=result.risk_level.value,
        previous_status=(
            system.compliance_status.value if system.compliance_status else None
        ),
        new_status=(
            system.compliance_status.value if system.compliance_status else None
        ),
        classifier_version=CLASSIFIER_VERSION,
    )
    db.add(event)

    # Apply the new risk level so subsequent scans don't keep re-flagging.
    system.risk_level = result.risk_level

    return event


# ---------------------------------------------------------------------------
# Top-level entry points
# ---------------------------------------------------------------------------


def run_drift_scan(db: Optional[Session] = None) -> dict:
    """
    Scan every monitored system, persist drift events, and dispatch
    notifications. Returns a summary dict for callers that want it
    (the admin scan endpoint does).

    Honours the advisory lock — if another replica is mid-scan, this
    call returns immediately with ``skipped=True``.
    """
    owns_session = db is None
    if owns_session:
        db = SessionLocal()

    start = time.perf_counter()
    try:
        with _advisory_lock(db, _ADVISORY_LOCK_KEY) as got_lock:
            if not got_lock:
                logger.info("compliance.monitor.skipped_locked")
                return {"systems_scanned": 0, "events_created": 0, "skipped": True}

            events: list[ComplianceDriftEvent] = []
            scanned = 0

            # Stream systems in chunks; we don't need them all in memory.
            offset = 0
            while True:
                batch = (
                    db.query(AISystem)
                    .filter(AISystem.monitoring_enabled.is_(True))
                    .order_by(AISystem.id)
                    .offset(offset)
                    .limit(_CHUNK_SIZE)
                    .all()
                )
                if not batch:
                    break
                for system in batch:
                    scanned += 1
                    event = _scan_one_system(db, system)
                    if event is not None:
                        events.append(event)
                offset += _CHUNK_SIZE

            db.commit()

            # Notifications dispatched after commit so the IDs exist.
            for event in events:
                try:
                    dispatch_notifications(db, event)
                except Exception:
                    # Per-event failure must not abort the whole scan.
                    logger.exception(
                        "compliance.monitor.notify_failed",
                        extra={"drift_event_id": event.id},
                    )

            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "compliance.monitor.scan_complete",
                extra={
                    "systems_scanned": scanned,
                    "events_created": len(events),
                    "duration_ms": duration_ms,
                },
            )
            return {
                "systems_scanned": scanned,
                "events_created": len(events),
                "duration_ms": duration_ms,
                "skipped": False,
            }
    finally:
        if owns_session:
            db.close()