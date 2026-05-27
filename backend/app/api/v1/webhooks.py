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
from typing import List

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


async def _async_deliver(url: str, headers: dict, payload_bytes: bytes, timeout: int = 5):
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            await client.post(url, content=payload_bytes, headers=headers)
    except Exception as exc:
        logger.warning("Webhook delivery to %s failed: %s", url, exc)


def deliver_webhook(
    db: Session,
    user_id: int,
    event: str,
    payload: dict,
    background_tasks: BackgroundTasks | None = None,
) -> None:
    """Dispatch webhook payloads for active webhook configs matching the event."""
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

            if background_tasks is not None:
                background_tasks.add_task(_async_deliver, w.url, headers, payload_bytes)
            else:
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