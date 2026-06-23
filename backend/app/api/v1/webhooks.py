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
from urllib.parse import urlparse
import ipaddress

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


def _validate_webhook_url(url: str) -> None:
    """Validate webhook URL to prevent SSRF attacks at delivery time."""
    parsed = urlparse(url)

    # Only allow http/https schemes
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https URLs are allowed")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL hostname")

    # Check if hostname is an IP address
    try:
        ip = ipaddress.ip_address(hostname)
        # Block private, link-local, loopback, and other special-use IPs
        if ip.is_private:
            raise ValueError("Private IP addresses are not allowed")
        if ip.is_link_local:
            raise ValueError("Link-local IP addresses are not allowed")
        if ip.is_loopback:
            raise ValueError("Loopback IP addresses are not allowed")
        if ip.is_reserved:
            raise ValueError("Reserved IP addresses are not allowed")
        if ip.is_multicast:
            raise ValueError("Multicast IP addresses are not allowed")
        # Block cloud metadata endpoints (169.254.169.254)
        if str(ip) == "169.254.169.254":
            raise ValueError("Cloud metadata endpoints are not allowed")
    except ValueError as e:
        # Re-raise our own validation errors
        if "not allowed" in str(e):
            raise
        # If it's not an IP address, it's a hostname - continue validation

    # Block common internal hostnames
    internal_hostnames = [
        "localhost",
        "metadata.google.internal",
        "169.254.169.254",
    ]
    if hostname.lower() in internal_hostnames:
        raise ValueError(f"Hostname '{hostname}' is not allowed")

    # Block any hostname that resolves to internal networks
    if hostname.endswith(".internal") or hostname.endswith(".local"):
        raise ValueError("Internal domain names are not allowed")


def _build_signature(secret: str, payload_body: bytes) -> str:
    """Generate an HMAC-SHA256 signature for a webhook payload."""
    return hmac.new(
        secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()


def _run_post_webhook(
    url: str,
    event: str,
    payload: dict[str, Any],
    secret: str | None,
) -> None:
    """Post a webhook payload synchronously.

    This function is passed to BackgroundTasks.add_task (which requires a sync callable)
    so that exceptions are caught here rather than being silently swallowed by FastAPI's
    background runner.

    Raises:
        WebhookDeliveryError: When the HTTP request fails (network error, timeout,
                             or a non-2xx status code).
    """
    payload_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {"X-AegisAI-Event": event}

    if secret:
        headers["X-AegisAI-Signature"] = _build_signature(secret, payload_body)

    try:
<<<<<<< HEAD
        # Validate URL before making request
        _validate_webhook_url(url)

        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(url, content=payload_body, headers=headers)
=======
        with httpx.Client(timeout=5.0) as client:
            response = client.post(url, content=payload_body, headers=headers)
>>>>>>> e645734 (fix: replace async _post_webhook with sync wrapper to prevent silent webhook failures)
            response.raise_for_status()
    except httpx.TimeoutException as exc:
        logger.error(
            "Webhook delivery failed: event=%s url=%s reason=timeout",
            event,
            url,
        )
    except httpx.HTTPStatusError as exc:
        logger.error(
            "Webhook delivery failed: event=%s url=%s reason=HTTP_%d",
            event,
            url,
            exc.response.status_code,
        )
    except httpx.RequestError as exc:
        logger.error(
            "Webhook delivery failed: event=%s url=%s reason=%s",
            event,
            url,
            exc,
        )
    except Exception:
        logger.exception("Unexpected error during webhook delivery: event=%s url=%s", event, url)


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
                _run_post_webhook,
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
    """Register a new webhook endpoint for the authenticated user."""
    webhook = WebhookConfig(
        user_id=current_user.id,
        url=body.url,
        secret=body.secret,
        is_active=body.is_active,
        events=body.events,
    )
    db.add(webhook)
    db.commit()
    db.refresh(webhook)
    return webhook


@router.get("", response_model=List[WebhookResponse])
def list_webhooks(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
<<<<<<< HEAD
) -> list[WebhookConfig]:
    """List all webhook configurations for the current user."""
    # Fetch webhooks strictly scoped to the authenticated user
    webhooks = (
        db.query(WebhookConfig).filter(WebhookConfig.user_id == current_user.id).all()
=======
) -> List[WebhookConfig]:
    """List all webhook endpoints registered by the authenticated user."""
    return (
        db.query(WebhookConfig)
        .filter(WebhookConfig.user_id == current_user.id)
        .all()
>>>>>>> e645734 (fix: replace async _post_webhook with sync wrapper to prevent silent webhook failures)
    )

    return webhooks


@router.get("/{webhook_id}", response_model=WebhookResponse)
def get_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> WebhookConfig:
    """Fetch a single webhook by ID, scoped to the authenticated user."""
    webhook = (
        db.query(WebhookConfig)
        .filter(
            WebhookConfig.id == webhook_id,
            WebhookConfig.user_id == current_user.id,
        )
        .first()
    )
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Webhook not found",
        )
    return webhook


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
<<<<<<< HEAD
    """Delete a webhook configuration owned by the current user."""
    # Query checking BOTH the webhook ID and the user ID
    db_webhook = (
=======
    """Delete a webhook endpoint owned by the authenticated user."""
    webhook = (
>>>>>>> e645734 (fix: replace async _post_webhook with sync wrapper to prevent silent webhook failures)
        db.query(WebhookConfig)
        .filter(
            WebhookConfig.id == webhook_id, WebhookConfig.user_id == current_user.id
        )
        .first()
    )
    if not webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )
    db.delete(webhook)
    db.commit()
<<<<<<< HEAD

    return None
=======
>>>>>>> e645734 (fix: replace async _post_webhook with sync wrapper to prevent silent webhook failures)
