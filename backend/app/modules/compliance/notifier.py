"""
Drift notification dispatcher.

Two channels:

* **In-app**: writes a ``Notification`` row to the AI system's owner.
* **Webhook**: POSTs a JSON payload to the per-system ``webhook_url``
  with an HMAC-SHA256 signature header. Retries on transient failures
  (network errors, 5xx) with exponential backoff. 4xx responses are
  treated as terminal - the operator's endpoint rejected us; no point
  retrying.

The payload format is documented in ``docs/compliance/drift-monitoring.md``
and stable for external integrations.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
from datetime import datetime
from typing import Optional

import httpx
from sqlalchemy.orm import Session
from tenacity import (
    retry,
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from app.core.config import settings
from app.models.ai_system import AISystem
from app.models.compliance_drift_event import ComplianceDriftEvent
from app.models.notification import Notification, NotificationType

logger = logging.getLogger("aegisai.compliance.notifier")

_WEBHOOK_TIMEOUT_SECONDS = 10.0


# ---------------------------------------------------------------------------
# Payload + signature
# ---------------------------------------------------------------------------


def _build_payload(event: ComplianceDriftEvent, system: AISystem) -> dict:
    return {
        "event_id": event.id,
        "event_type": "compliance.drift_detected",
        "detected_at": event.detected_at.isoformat() + "Z",
        "ai_system": {
            "id": system.id,
            "name": system.name,
        },
        "drift": {
            "type": event.drift_type.value
            if hasattr(event.drift_type, "value")
            else str(event.drift_type),
            "previous_risk_level": event.previous_risk_level,
            "new_risk_level": event.new_risk_level,
            "previous_status": event.previous_status,
            "new_status": event.new_status,
            "classifier_version": event.classifier_version,
        },
    }


def _sign(body: bytes, secret: str) -> str:
    digest = hmac.new(secret.encode("utf-8"), body, hashlib.sha256).hexdigest()
    return f"sha256={digest}"


# ---------------------------------------------------------------------------
# In-app
# ---------------------------------------------------------------------------


def _notify_in_app(db: Session, event: ComplianceDriftEvent, system: AISystem) -> None:
    title, message = _format_message(event, system)
    db.add(
        Notification(
            user_id=system.owner_id,
            notification_type=NotificationType.COMPLIANCE_DRIFT.value,
            title=title,
            message=message,
            resource_type="ai_system",
            resource_id=system.id,
        )
    )
    event.notified_in_app = True


def _format_message(
    event: ComplianceDriftEvent, system: AISystem
) -> tuple[str, str]:
    drift = event.drift_type.value if hasattr(event.drift_type, "value") else str(event.drift_type)
    if drift in ("risk_change", "mixed"):
        title = f"Risk level changed: {system.name}"
        message = (
            f"Scheduled re-classification detected a risk-level change for "
            f"'{system.name}': {event.previous_risk_level or 'unset'} → "
            f"{event.new_risk_level or 'unset'}."
        )
    elif drift == "classifier_version_change":
        title = f"Classifier updated: review {system.name}"
        message = (
            f"The risk classifier was updated to version "
            f"{event.classifier_version}. '{system.name}' was re-evaluated "
            "against the new logic — review recommended."
        )
    else:
        title = f"Compliance drift detected: {system.name}"
        message = (
            f"Scheduled monitoring detected a {drift} for '{system.name}'."
        )
    return title, message


# ---------------------------------------------------------------------------
# Webhook
# ---------------------------------------------------------------------------


class _RetryableWebhookError(Exception):
    """Raised when the webhook target returned a 5xx or had a network error."""


@retry(
    retry=retry_if_exception_type(_RetryableWebhookError),
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=1, max=10),
    reraise=True,
)
def _deliver_webhook(url: str, body: bytes, signature: str) -> httpx.Response:
    """Single delivery attempt with tenacity retry around it."""
    try:
        response = httpx.post(
            url,
            content=body,
            headers={
                "Content-Type": "application/json",
                "X-AegisAI-Signature": signature,
                "User-Agent": f"AegisAI-Webhook/{getattr(settings, 'VERSION', '0.1.0')}",
            },
            timeout=_WEBHOOK_TIMEOUT_SECONDS,
        )
    except (httpx.TimeoutException, httpx.NetworkError) as exc:
        raise _RetryableWebhookError(f"network/timeout: {exc}") from exc

    if 500 <= response.status_code < 600:
        raise _RetryableWebhookError(f"server error {response.status_code}")
    return response


def _notify_webhook(
    db: Session, event: ComplianceDriftEvent, system: AISystem
) -> None:
    """Best-effort webhook delivery. Records outcome on the event row."""
    if not system.webhook_url:
        return
    if not system.webhook_secret:
        logger.warning(
            "compliance.notifier.webhook_no_secret",
            extra={"ai_system_id": system.id, "drift_event_id": event.id},
        )
        event.webhook_error = "webhook_url set but webhook_secret missing"
        return

    payload = _build_payload(event, system)
    # canonical body — exact bytes the signature covers
    body = json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")
    signature = _sign(body, system.webhook_secret)

    try:
        response = _deliver_webhook(system.webhook_url, body, signature)
        event.webhook_response_code = response.status_code
        event.webhook_delivered_at = datetime.utcnow()
        if response.status_code >= 400:
            event.webhook_error = (
                response.text[:500] or f"HTTP {response.status_code}"
            )
            logger.warning(
                "compliance.notifier.webhook_client_error",
                extra={
                    "ai_system_id": system.id,
                    "drift_event_id": event.id,
                    "status_code": response.status_code,
                },
            )
        else:
            logger.info(
                "compliance.notifier.webhook_delivered",
                extra={
                    "ai_system_id": system.id,
                    "drift_event_id": event.id,
                    "status_code": response.status_code,
                },
            )
    except _RetryableWebhookError as exc:
        event.webhook_error = str(exc)[:500]
        logger.warning(
            "compliance.notifier.webhook_giveup",
            extra={
                "ai_system_id": system.id,
                "drift_event_id": event.id,
                "error": str(exc),
            },
        )


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def dispatch_notifications(db: Session, event: ComplianceDriftEvent) -> None:
    """Send both in-app and webhook (if configured) for a drift event.

    The caller is responsible for committing the session afterwards.
    """
    system: Optional[AISystem] = (
        db.query(AISystem).filter(AISystem.id == event.ai_system_id).first()
    )
    if system is None:  # pragma: no cover — referential integrity should prevent this
        return

    _notify_in_app(db, event, system)
    _notify_webhook(db, event, system)
    db.commit()