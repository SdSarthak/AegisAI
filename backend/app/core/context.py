"""Request-scoped context shared across async call stacks.

The middleware layer stores a request id here and the auth dependency stores
the current user id here. Logging, telemetry, and request handlers can then
read the same values without explicitly threading them through every call.

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
    """Return the active request id, or ``None`` outside a request."""
    return request_id_ctx.get()


def get_user_id() -> Optional[int]:
    """Return the current user id, or ``None`` for anonymous requests."""
    return user_id_ctx.get()
