"""
Webhooks API — configure outbound event delivery URLs.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only

TODO for contributors (help wanted):
  - Implement webhook delivery: when a Guard block decision is made in
    POST /guard/scan, call `deliver_webhook(db, user_id, event="guard_block", payload={...})`.
    Use `httpx` (already in requirements) to POST the payload to the configured URL.
    Sign the body with HMAC-SHA256 using the stored secret and set the
    X-AegisAI-Signature header.
  - Acceptance criteria: configuring a webhook URL and triggering a guard
    block results in a POST request to that URL within 5 seconds.
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
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
from app.models.webhook import WebhookConfig  # Assuming this is the SQLAlchemy model
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
    background_tasks: BackgroundTasks,
) -> None:
    """Schedule delivery to active user webhooks subscribed to the event."""
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

        background_tasks.add_task(
            _post_webhook,
            url=webhook.url,
            event=event,
            payload=payload,
            secret=webhook.secret,
        )


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    body: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    """Register a new webhook endpoint for the current user."""
    # Force the user_id to be the authenticated user to prevent spoofing
    webhook_data = body.model_dump()
    db_webhook = WebhookConfig(
        **webhook_data,
        user_id=current_user.id
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

    """List all webhook configurations for the current user."""
    # Fetch webhooks strictly scoped to the authenticated user
    webhooks = db.query(WebhookConfig).filter(WebhookConfig.user_id == current_user.id).all()
    
    return webhooks


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    """Delete a webhook configuration owned by the current user."""
    # Query checking BOTH the webhook ID and the user ID
    db_webhook = db.query(WebhookConfig).filter(
        WebhookConfig.id == webhook_id,
        WebhookConfig.user_id == current_user.id
    ).first()

    # Generic 404 error (hides existence of other users' webhooks)
    if not db_webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found"
        )

    db.delete(db_webhook)
    db.commit()
    
    return None
