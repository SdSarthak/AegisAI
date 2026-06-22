"""
Webhooks API - configure outbound event delivery URLs.

Changed: Resolved merge conflicts while preserving user-scoped webhook CRUD.
Why: Webhooks must not be creatable or deletable on behalf of another user.
Addresses: Cross-user webhook access and broken imports/docstrings after merge.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import hashlib
import hmac
import json
import logging
from typing import Any, List

import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.webhook import WebhookConfig
from app.schemas.webhook import WebhookCreate, WebhookResponse

router = APIRouter()
logger = logging.getLogger(__name__)


class WebhookDeliveryError(Exception):
    """Raised when a webhook payload fails to reach its configured endpoint."""

    def __init__(
        self,
        url: str,
        event: str,
        reason: str,
    ) -> None:
        super().__init__(f"Webhook delivery failed for event={event} url={url}: {reason}")
        self.url = url
        self.event = event
        self.reason = reason


def _build_signature(secret: str, payload_body: bytes) -> str:
    """Generate an HMAC-SHA256 signature for a webhook payload."""
    return hmac.new(
        secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()


async def _post_webhook(
    url: str,
    event: str,
    payload: dict[str, Any],
    secret: str | None,
) -> None:
    """Post a webhook payload to a configured endpoint.

    Raises:
        WebhookDeliveryError: When the HTTP request fails (network error, timeout,
                             or a non-2xx status code).
    """
    payload_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {"X-AegisAI-Event": event}

    if secret:
        headers["X-AegisAI-Signature"] = _build_signature(secret, payload_body)

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, content=payload_body, headers=headers)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        raise WebhookDeliveryError(
            url=url,
            event=event,
            reason=f"timeout after {exc.args[0] if exc.args else '5s'} (request timed out)",
        ) from exc
    except httpx.HTTPStatusError as exc:
        raise WebhookDeliveryError(
            url=url,
            event=event,
            reason=f"HTTP {exc.response.status_code} {exc.response.reason_phrase}",
        ) from exc
    except httpx.RequestError as exc:
        raise WebhookDeliveryError(
            url=url,
            event=event,
            reason=f"request error: {exc}",
        ) from exc


def deliver_webhook(
    db: Session,
    user_id: int,
    event: str,
    payload: dict[str, Any],
    background_tasks: BackgroundTasks,
) -> None:
    """Schedule delivery to active user webhooks subscribed to the event.

    Raises:
        WebhookDeliveryError: When a background task cannot be scheduled
                           for a subscribed webhook (e.g. task queue full).
    """
    webhooks = (
        db.query(WebhookConfig)
        .filter(
            WebhookConfig.user_id == user_id,
            WebhookConfig.is_active.is_(True),
        )
        .all()
    )

    for webhook in webhooks:
        if event not in (webhook.events or []):
            continue

        try:
            background_tasks.add_task(
                _post_webhook,
                url=webhook.url,
                event=event,
                payload=payload,
                secret=webhook.secret,
            )
        except Exception as exc:  # noqa: BLE001
            raise WebhookDeliveryError(
                url=webhook.url,
                event=event,
                reason=f"failed to schedule background task: {exc}",
            ) from exc


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    body: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WebhookConfig:
    """Register a new webhook endpoint for the current user."""
    webhook_data = body.model_dump()
    db_webhook = WebhookConfig(**webhook_data, user_id=current_user.id)

    db.add(db_webhook)
    db.commit()
    db.refresh(db_webhook)

    return db_webhook


@router.get("", response_model=List[WebhookResponse])
def list_webhooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WebhookConfig]:
    """List all webhook configurations for the current user."""
    return (
        db.query(WebhookConfig)
        .filter(WebhookConfig.user_id == current_user.id)
        .all()
    )


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a webhook configuration owned by the current user."""
    db_webhook = (
        db.query(WebhookConfig)
        .filter(
            WebhookConfig.id == webhook_id,
            WebhookConfig.user_id == current_user.id,
        )
        .first()
    )

    if not db_webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    db.delete(db_webhook)
    db.commit()
    return None
