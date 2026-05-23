"""Webhooks API for outbound event delivery."""

import asyncio
import hashlib
import hmac
import json
import logging

import httpx
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.models.user import User
from app.schemas.webhook_config import WebhookConfigCreate, WebhookConfigOut

try:
    from app.core.deps import get_current_user, get_db
except ModuleNotFoundError:
    from app.core.database import get_db
    from app.core.security import get_current_user

try:
    from app.models.webhook_config import WebhookConfig
except ModuleNotFoundError:
    from app.models.webhook import WebhookConfig

router = APIRouter()
logger = logging.getLogger(__name__)


@router.post("", response_model=WebhookConfigOut, status_code=status.HTTP_201_CREATED)
async def create_webhook(
    body: WebhookConfigCreate,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WebhookConfig:
    """Register a new webhook endpoint for the current user."""
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
async def list_webhooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> list[WebhookConfig]:
    """List all webhook configs for the current user."""
    return (
        db.query(WebhookConfig)
        .filter(WebhookConfig.user_id == current_user.id)
        .all()
    )


@router.delete("/{webhook_id}", status_code=status.HTTP_200_OK)
async def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> dict[str, str]:
    """Delete a webhook config owned by the current user."""
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
    return {"detail": "deleted"}


async def deliver_webhook(
    db: Session,
    user_id: int,
    event: str,
    payload: dict,
) -> None:
    """Deliver an event payload to all matching active webhook configs."""
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
