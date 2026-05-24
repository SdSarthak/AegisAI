"""
Request context middleware.

A pure ASGI middleware (not ``BaseHTTPMiddleware``) so the ContextVars it
sets propagate correctly into route handlers and their dependencies — the
well-known Starlette gotcha is that ``BaseHTTPMiddleware`` runs the endpoint
in a separate anyio task, which breaks ContextVar propagation. Implementing
the middleware at the ASGI layer keeps everything in one context.

Responsibilities:
  * Read an inbound ``X-Request-ID`` (or mint a new one) and bind it to the
    ``request_id`` ContextVar for the lifetime of the request.
  * Echo the id back as the ``X-Request-ID`` response header.
  * Emit a structured ``request.completed`` access log with method, path,
    status, and duration — in JSON, with request_id and (if the auth
    dependency ran) user_id attached automatically by the log formatter.
  * Log unhandled exceptions with the request id before re-raising.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import logging
import re
import time
from uuid import uuid4

from starlette.datastructures import Headers, MutableHeaders
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.core.context import request_id_ctx, user_id_ctx

logger = logging.getLogger("aegisai.access")

_REQUEST_ID_HEADER = "x-request-id"
# Accept only sane inbound ids (uuid hex, dashes, alphanumerics); otherwise
# mint our own so a client can't inject newlines/huge values into our logs.
_SAFE_REQUEST_ID = re.compile(r"^[A-Za-z0-9._-]{1,128}$")


def _resolve_request_id(headers: Headers) -> str:
    incoming = headers.get(_REQUEST_ID_HEADER)
    if incoming and _SAFE_REQUEST_ID.match(incoming):
        return incoming
    return uuid4().hex


class RequestContextMiddleware:
    """Bind a request id to the async context and emit a JSON access log."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self, scope: Scope, receive: Receive, send: Send
    ) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = Headers(scope=scope)
        request_id = _resolve_request_id(headers)
        rid_token = request_id_ctx.set(request_id)
        # Reset any user id leaked from a pooled context; the auth dependency
        # sets it again for authenticated requests.
        uid_token = user_id_ctx.set(None)

        method = scope.get("method", "-")
        path = scope.get("path", "-")
        start = time.perf_counter()
        status_holder = {"code": 500}

        async def send_wrapper(message: Message) -> None:
            if message["type"] == "http.response.start":
                status_holder["code"] = message["status"]
                mutable = MutableHeaders(scope=message)
                mutable["X-Request-ID"] = request_id
            await send(message)

        try:
            await self.app(scope, receive, send_wrapper)
        except Exception:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.exception(
                "request.failed",
                extra={
                    "http_method": method,
                    "http_path": path,
                    "status_code": 500,
                    "duration_ms": duration_ms,
                },
            )
            raise
        else:
            duration_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.info(
                "request.completed",
                extra={
                    "http_method": method,
                    "http_path": path,
                    "status_code": status_holder["code"],
                    "duration_ms": duration_ms,
                },
            )
        finally:
            user_id_ctx.reset(uid_token)
            request_id_ctx.reset(rid_token)
