"""
Request-scoped context propagated through async call stacks.

These ContextVars are populated by ``RequestContextMiddleware`` (request_id)
and by ``get_current_user`` in ``app.core.security`` (user_id). The JSON log
formatter in ``app.core.logging`` reads them so every log line emitted while
handling a request carries the same ``request_id`` and, when authenticated,
the ``user_id`` — without threading those values through every function call.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

from contextvars import ContextVar
from typing import Optional

# Set once per request by the ASGI middleware. ``None`` outside a request
# (e.g. startup logs, CLI scripts, background jobs without a request).
request_id_ctx: ContextVar[Optional[str]] = ContextVar("request_id", default=None)

# Set by the auth dependency once a JWT has been validated. Stays ``None``
# for anonymous / unauthenticated requests.
user_id_ctx: ContextVar[Optional[int]] = ContextVar("user_id", default=None)


def get_request_id() -> Optional[str]:
    """Return the current request id, or ``None`` if not inside a request.

    Returns:
        The active request id propagated by the ASGI middleware.
    """
    return request_id_ctx.get()


def get_user_id() -> Optional[int]:
    """Return the authenticated user id, or ``None`` if unauthenticated.

    Returns:
        The authenticated user id attached by the auth dependency.
    """
    return user_id_ctx.get()
