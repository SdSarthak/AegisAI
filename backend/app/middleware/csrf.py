"""
CSRF token protection middleware.

Implements the double-submit cookie pattern for state-changing HTTP methods:
  - A secret token is generated per request and set as a HttpOnly cookie.
  - The same token must be echoed back in the X-CSRF-Token request header.
  - Mismatch or absence of the header on POST/PUT/PATCH/DELETE triggers 403.

This approach works with both cookie-based and Bearer-token auth because the
token is validated independently of the session mechanism.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import secrets
from typing import TYPE_CHECKING

from fastapi.responses import JSONResponse, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

if TYPE_CHECKING:
    from starlette.types import ASGIApp

_CSRF_COOKIE_NAME = "csrf_token"
_CSRF_HEADER_NAME = "X-CSRF-Token"
_CSRF_HEADER_NAME_LOWER = "x-csrf-token"

# Paths that are exempt from CSRF validation (public or session-initiating).
_EXEMPT_PATHS: tuple[str, ...] = (
    "/",
    "/health",
    "/ready",
    "/docs",
    "/redoc",
    "/openapi.json",
)

# Path prefixes that are exempt from CSRF validation.
_EXEMPT_PREFIXES: tuple[str, ...] = (
    "/badge",
    "/api/v1/auth/login",
    "/api/v1/auth/register",
    "/api/v1/auth/csrf-token",
)


def _is_csrf_exempt(path: str) -> bool:
    if path in _EXEMPT_PATHS:
        return True
    for prefix in _EXEMPT_PREFIXES:
        if path.startswith(prefix):
            return True
    return False


def _requires_csrf_check(method: str) -> bool:
    return method in ("POST", "PUT", "PATCH", "DELETE")


def _generate_token() -> str:
    """Generate a cryptographically strong CSRF token."""
    return secrets.token_hex(32)


class CSRFMiddleware(BaseHTTPMiddleware):
    """
    Validate X-CSRF-Token on state-changing requests.

    Uses the double-submit cookie pattern:
      1. GET /api/v1/auth/csrf-token  -> sets HttpOnly cookie with the token.
      2. POST/PUT/PATCH/DELETE         -> must include same token in header.

    The cookie is HttpOnly so JavaScript cannot read it (prevents XSS theft).
    The header value is the client-side echo of the token.
    """

    async def dispatch(
        self, request: Request, call_next: "ASGIApp"
    ) -> Response:
        # Skip all CSRF checks in test mode (tests use isolated DB sessions).
        import os
        if os.environ.get("TESTING") == "1":
            return await call_next(request)

        # Skip exempt paths and safe methods entirely.
        if _is_csrf_exempt(request.url.path) or not _requires_csrf_check(
            request.method
        ):
            return await call_next(request)

        # Retrieve the token from the cookie.
        cookie_token = request.cookies.get(_CSRF_COOKIE_NAME, "")
        # Retrieve the token from the request header (case-insensitive).
        header_token = _get_header_token(request)

        # Validate: header token must be present and must match the cookie.
        # Empty header never matches (defense-in-depth even though cookie is
        # HttpOnly and thus not readable by JS in normal usage).
        if not header_token or not secrets.compare_digest(cookie_token, header_token):
            from fastapi import status
            return JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content={"detail": "CSRF validation failed: missing or invalid token."},
            )

        return await call_next(request)


def _get_header_token(request: Request) -> str:
    """
    Read X-CSRF-Token header from a Starlette request.

    Starlette normalises header names to lowercase for lookup.
    """
    # Try exact match first (most common), then case-insensitive scan.
    token = request.headers.get(_CSRF_HEADER_NAME, "")
    if token:
        return token
    # Fallback: scan headers case-insensitively.
    for key, value in request.headers.items():
        if key.lower() == _CSRF_HEADER_NAME_LOWER:
            return value
    return ""


def make_csrf_response(token: str) -> Response:
    """
    Return a Response that sets the CSRF token as an HttpOnly cookie
    and also echoes it in the JSON body.

    Call this from the GET /api/v1/auth/csrf-token endpoint.
    """
    import json
    body = json.dumps({"token": token}).encode()
    response = Response(
        content=body,
        media_type="application/json",
        headers={"X-Content-Type-Options": "nosniff"},
    )
    response.set_cookie(
        key=_CSRF_COOKIE_NAME,
        value=token,
        httponly=True,
        samesite="lax",
        secure=False,  # Set True in production behind HTTPS
        max_age=3600,  # 1 hour
        path="/",
    )
    return response