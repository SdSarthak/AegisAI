"""
Webhooks API — configure outbound event delivery URLs.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import asyncio
import hashlib
import hmac
import json
import logging
from typing import Any, List

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.webhook import WebhookConfig
from app.schemas.webhook import WebhookCreate, WebhookResponse

router = APIRouter()
logger = logging.getLogger(__name__)


def _build_signature(secret: str, payload_body: bytes) -> str:
    """Generate HMAC-SHA256 signature for webhook payload."""
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
    """Post webhook payload to a configured endpoint."""
    try:
        payload_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")

        headers = {
            "X-AegisAI-Event": event,
        }

        if secret:
            headers["X-AegisAI-Signature"] = _build_signature(secret, payload_body)

        async with httpx.AsyncClient(timeout=5.0) as client:
            await client.post(
                url,
                content=payload_body,
                headers=headers,
            )
    except Exception:
        logger.exception("Webhook delivery failed for event=%s url=%s", event, url)


def deliver_webhook(
    db: Session,
    user_id: int,
    event: str,
    payload: dict[str, Any],
) -> None:
    """
    Fire-and-forget delivery to active user webhooks subscribed to the event.

    Delivery failures are logged and never block the caller.
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
        subscribed_events = webhook.events or []

        if event not in subscribed_events:
            continue

        try:
            asyncio.create_task(
                _post_webhook(
                    url=webhook.url,
                    event=event,
                    payload=payload,
                    secret=webhook.secret,
                )
            )
        except RuntimeError:
            logger.exception(
                "Webhook delivery could not be scheduled for event=%s url=%s",
                event,
                webhook.url,
            )


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    body: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register a new webhook endpoint for the current user."""
    webhook_data = body.model_dump()
    webhook_data["url"] = str(body.url)

    db_webhook = WebhookConfig(
        **webhook_data,
        user_id=current_user.id,
    )

    db.add(db_webhook)
    db.commit()
    db.refresh(db_webhook)

    return db_webhook


@router.get("", response_model=List[WebhookResponse])
def list_webhooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """List all webhook configs for the current user."""
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
):
    """Delete a webhook config belonging to the current user."""
    db_webhook = (
        db.query(WebhookConfig)
        .filter(
            WebhookConfig.id == webhook_id,
            WebhookConfig.user_id == current_user.id,
        )
        .first()
    )

    if db_webhook is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    db.delete(db_webhook)
    db.commit()

    return None