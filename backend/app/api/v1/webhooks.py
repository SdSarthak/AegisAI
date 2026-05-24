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

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.webhook import WebhookConfig
from app.schemas.webhook import WebhookConfigCreate, WebhookConfigOut

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=WebhookConfigOut, status_code=status.HTTP_201_CREATED)
def create_webhook(
    body: WebhookConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WebhookConfig:
    """Register a new webhook endpoint for the current user.

    Args:
        body: Payload containing the webhook URL and event configuration.
        current_user: The authenticated user extracted from the JWT token.
        db: Database session dependency.

    Returns:
        WebhookConfig: The newly created webhook configuration with HTTP 201.
    """
    config = WebhookConfig(
        user_id=current_user.id,
        url=str(body.url),
        events=body.events,
        secret=body.secret,
        is_active=True,
    )
    db.add(config)
    db.commit()
    db.refresh(config)
    return config


@router.get("", response_model=list[WebhookConfigOut])
def list_webhooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WebhookConfig]:
    """List all webhook configurations for the current user.

    Args:
        current_user: The authenticated user extracted from the JWT token.
        db: Database session dependency.

    Returns:
        List[WebhookConfigOut]: All webhook configs belonging to the current user.
    """
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
    """Delete a webhook configuration belonging to the current user.

    Args:
        webhook_id: The unique identifier of the webhook to delete.
        current_user: The authenticated user extracted from the JWT token.
        db: Database session dependency.

    Returns:
        None: HTTP 204 No Content on success.

    Raises:
        HTTPException: 404 if webhook not found or not owned by user.
    """
    config = (
        db.query(WebhookConfig)
        .filter(
            WebhookConfig.id == webhook_id,
            WebhookConfig.user_id == current_user.id,
        )
        .first()
    )

    if config is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )

    db.delete(config)
    db.commit()


async def deliver_webhook(
    db: Session,
    user_id: int,
    event: str,
    payload: dict,
) -> None:
    """Deliver an event payload to all matching active webhook configs.

    Args:
        db: Database session.
        user_id: The user whose webhook configs to query.
        event: The event type to deliver (e.g. "guard_block").
        payload: The JSON-serializable payload to send.
    """
    configs = (
        db.query(WebhookConfig)
        .filter(
            WebhookConfig.user_id == user_id,
            WebhookConfig.is_active.is_(True),
            WebhookConfig.events.contains([event]),
        )
        .all()
    )

    async def _deliver(config: WebhookConfig) -> None:
        try:
            body = json.dumps(payload, separators=(",", ":")).encode()
            secret = config.secret or ""
            sig = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()

            async with httpx.AsyncClient(timeout=10.0) as client:
                await client.post(
                    config.url,
                    content=body,
                    headers={
                        "Content-Type": "application/json",
                        "X-AegisAI-Event": event,
                        "X-AegisAI-Signature": f"sha256={sig}",
                    },
                )
        except Exception as e:
            logger.warning("Webhook delivery failed url=%s error=%s", config.url, e)

    tasks = [asyncio.create_task(_deliver(config)) for config in configs]
    if tasks:
        await asyncio.gather(*tasks, return_exceptions=True)
