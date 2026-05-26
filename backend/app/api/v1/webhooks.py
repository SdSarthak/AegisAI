"""
Webhooks API — configure outbound event delivery URLs.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from typing import List

from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.models.webhook import WebhookConfig
from app.schemas.webhook import WebhookCreate, WebhookResponse
import asyncio
import json
import hmac
import hashlib
import logging
import httpx

router = APIRouter()
logger = logging.getLogger(__name__)


async def _async_deliver(url: str, headers: dict, payload_bytes: bytes, timeout: int = 5):
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            await client.post(url, content=payload_bytes, headers=headers)
    except Exception as exc:
        logger.warning("Webhook delivery to %s failed: %s", url, exc)


def deliver_webhook(db: Session, user_id: int, event: str, payload: dict, background_tasks: BackgroundTasks | None = None) -> None:
    """Dispatch webhook payloads for active webhook configs matching the event.

    This schedules an async background delivery using `asyncio.create_task` so
    it does not block request handling. Failures are logged at WARNING level.
    """
    # Query active webhooks for this user that subscribe to the event
    configs = (
        db.query(WebhookConfig)
        .filter(WebhookConfig.user_id == user_id, WebhookConfig.is_active == True)
        .all()
    )

    if not configs:
        return

    payload_bytes = json.dumps({"event": event, "payload": payload}).encode("utf-8")

    for w in configs:
        try:
            if w.events and event not in (w.events or []):
                continue

            headers = {
                "Content-Type": "application/json",
                "X-AegisAI-Event": event,
            }

            if w.secret:
                sig = hmac.new(w.secret.encode("utf-8"), payload_bytes, hashlib.sha256).hexdigest()
                headers["X-AegisAI-Signature"] = sig

            # Schedule async delivery via FastAPI BackgroundTasks when available
            if background_tasks is not None:
                try:
                    background_tasks.add_task(_async_deliver, w.url, headers, payload_bytes)
                except Exception:
                    # If BackgroundTasks.add_task fails for some reason, fallback
                    asyncio.get_event_loop().run_until_complete(_async_deliver(w.url, headers, payload_bytes))
            else:
                # No BackgroundTasks provided: try scheduling on the running loop
                try:
                    asyncio.create_task(_async_deliver(w.url, headers, payload_bytes))
                except RuntimeError:
                    asyncio.get_event_loop().run_until_complete(_async_deliver(w.url, headers, payload_bytes))

        except Exception as exc:
            logger.warning("Failed to schedule webhook delivery for %s: %s", getattr(w, "url", "<unknown>"), exc)


@router.post("", response_model=WebhookResponse, status_code=status.HTTP_201_CREATED)
def create_webhook(
    body: WebhookCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Register a new webhook endpoint for the current user.

    Args:
        body: Payload containing the webhook URL and event configuration.
        current_user: The authenticated user extracted from the JWT token.
        db: Database session dependency.

    Returns:
        WebhookResponse: The newly created webhook configuration with HTTP 201.
    """
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
    """List all webhook configurations for the current user.

    Args:
        current_user: The authenticated user extracted from the JWT token.
        db: Database session dependency.

    Returns:
        List[WebhookResponse]: All webhook configs belonging to the current user.
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
):
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
