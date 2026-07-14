"""
Webhooks API - configure outbound event delivery URLs.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import hashlib
import hmac
import json
import logging
import socket
import time
from typing import Any, List
from urllib.parse import urlparse
import ipaddress

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

# IP ranges that are never allowed for webhook delivery
BLOCKED_IP_NETWORKS = [
    ipaddress.ip_network("10.0.0.0/8"),
    ipaddress.ip_network("172.16.0.0/12"),
    ipaddress.ip_network("192.168.0.0/16"),
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("169.254.0.0/16"),
    ipaddress.ip_network("::1/128"),
    ipaddress.ip_network("fc00::/7"),
    ipaddress.ip_network("fe80::/10"),
]

CLOUD_METADATA_IPS = [
    ipaddress.ip_address("169.254.169.254"),
    ipaddress.ip_address("100.100.100.200"),
    ipaddress.ip_address("192.0.0.192"),
]

INTERNAL_HOSTNAME_SUFFIXES = [
    ".internal",
    ".local",
    ".lan",
    ".intranet",
    ".private",
    ".corp",
]

INTERNAL_HOSTNAME_EXACT = [
    "localhost",
    "metadata.google.internal",
    "metadata.aws.internal",
    "metadata.azure.internal",
    "100.100.100.200",
    "192.0.0.192",
]

DNS_REBINDING_TTL_THRESHOLD = 300


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


def _is_ip_blocked(ip: ipaddress.IPv4Address | ipaddress.IPv6Address) -> bool:
    """Check if an IP address falls into any blocked range."""
    if ip.is_private or ip.is_loopback or ip.is_link_local or ip.is_reserved or ip.is_multicast:
        return True
    for network in BLOCKED_IP_NETWORKS:
        if ip in network:
            return True
    if ip in CLOUD_METADATA_IPS:
        return True
    return False


def _validate_webhook_url(url: str) -> None:
    """Validate webhook URL to prevent SSRF attacks at delivery time."""
    parsed = urlparse(url)

    # Only allow http/https schemes
    if parsed.scheme not in ("http", "https"):
        raise ValueError("Only http and https URLs are allowed")

    hostname = parsed.hostname
    if not hostname:
        raise ValueError("Invalid URL hostname")

    # Check if hostname is an IP address directly
    try:
        ip = ipaddress.ip_address(hostname)
        if _is_ip_blocked(ip):
            raise ValueError(f"IP address {hostname} is not allowed")
        return
    except ValueError as e:
        if "not allowed" in str(e):
            raise

    # Block exact-match internal hostnames
    if hostname.lower() in INTERNAL_HOSTNAME_EXACT:
        raise ValueError(f"Hostname '{hostname}' is not allowed")

    # Block internal hostname suffix patterns
    for suffix in INTERNAL_HOSTNAME_SUFFIXES:
        if hostname.lower().endswith(suffix):
            raise ValueError(f"Hostname '{hostname}' has a blocked suffix '{suffix}'")

    # Resolve ALL IPs for the hostname and validate each
    try:
        results = socket.getaddrinfo(hostname, None)
        resolved_ips = set()
        for result in results:
            ip = ipaddress.ip_address(result[4][0])
            resolved_ips.add(ip)
            if _is_ip_blocked(ip):
                raise ValueError(f"Hostname '{hostname}' resolves to blocked IP {ip}")
    except socket.gaierror as e:
        raise ValueError(f"Could not resolve hostname '{hostname}': {e}")


def _build_signature(secret: str, payload_body: bytes) -> str:
    """Generate an HMAC-SHA256 signature for a webhook payload."""
    return hmac.new(
        secret.encode("utf-8"),
        payload_body,
        hashlib.sha256,
    ).hexdigest()


def _post_webhook(
    url: str,
    event: str,
    payload: dict[str, Any],
    secret: str | None,
) -> None:
    """Post a webhook payload to a configured endpoint with retry logic."""
    max_retries = 3
    payload_body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    headers = {"X-AegisAI-Event": event}

    if secret:
        headers["X-AegisAI-Signature"] = _build_signature(secret, payload_body)

    _validate_webhook_url(url)

    for attempt in range(max_retries):
        try:
            with httpx.Client(timeout=5.0) as client:
                response = client.post(url, content=payload_body, headers=headers)
                response.raise_for_status()
            return
        except Exception as exc:
            if attempt < max_retries - 1:
                wait = 2 ** attempt
                logger.warning(
                    "Webhook attempt %d/%d failed for %s, retrying in %ds: %s",
                    attempt + 1, max_retries, url, wait, exc,
                )
                time.sleep(wait)
            else:
                logger.exception(
                    "Webhook delivery failed after %d attempts for event=%s url=%s",
                    max_retries, event, url,
                )


def deliver_webhook(
    db: Session,
    user_id: int,
    event: str,
    payload: dict[str, Any],
) -> None:
    """Deliver event to active user webhooks subscribed to the event."""
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

        _post_webhook(
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
    # Fetch webhooks strictly scoped to the authenticated user
    webhooks = (
        db.query(WebhookConfig).filter(WebhookConfig.user_id == current_user.id).all()
    )

    return webhooks


@router.delete("/{webhook_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_webhook(
    webhook_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> None:
    """Delete a webhook configuration owned by the current user."""
    # Query checking BOTH the webhook ID and the user ID
    db_webhook = (
        db.query(WebhookConfig)
        .filter(
            WebhookConfig.id == webhook_id, WebhookConfig.user_id == current_user.id
        )
        .first()
    )

    if not db_webhook:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Webhook not found"
        )

    db.delete(db_webhook)
    db.commit()

    return None
