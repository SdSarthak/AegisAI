"""
Pydantic schemas for WebhookConfig resource.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from datetime import datetime
from typing import Optional
from urllib.parse import urlparse
import ipaddress

from pydantic import BaseModel, Field, HttpUrl, field_validator


class WebhookCreate(BaseModel):
    url: HttpUrl
    secret: Optional[str] = None
    events: list[str] = Field(default_factory=list)

    @field_validator("url")
    @classmethod
    def validate_webhook_url(cls, v):
        """Validate webhook URL to prevent SSRF attacks."""
        parsed = urlparse(str(v))

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
        # This is a basic check - in production, you'd want DNS resolution checks
        if hostname.endswith(".internal") or hostname.endswith(".local"):
            raise ValueError("Internal domain names are not allowed")

        return v


class WebhookResponse(BaseModel):
    id: int
    url: str
    is_active: bool
    events: list[str]
    created_at: datetime

    class Config:
        from_attributes = True
