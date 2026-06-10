"""JSON logging helpers for the AegisAI backend.

The backend emits structured logs instead of ad hoc text so request ids,
user ids, service metadata, and caller-provided ``extra`` fields remain
queryable by log aggregation tools without regex parsing. This module owns
the formatter and root logger setup used by the API process.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from __future__ import annotations

import hashlib
import logging
import sys
from datetime import datetime, timezone
from typing import Any

from pythonjsonlogger import jsonlogger

from app.core.context import request_id_ctx, user_id_ctx

SERVICE_NAME = "aegis-backend"
SERVICE_VERSION = "0.1.0"

# Loggers whose noisy default handlers we replace so their output is JSON too.
_THIRD_PARTY_LOGGERS = (
    "uvicorn",
    "uvicorn.error",
    "uvicorn.access",
    "gunicorn.error",
    "gunicorn.access",
    "sqlalchemy.engine",
)

# Standard LogRecord attributes — anything *not* in here that appears on the
# record is treated as a caller-supplied ``extra`` and promoted to a top-level
# JSON key.
_RESERVED_RECORD_ATTRS = frozenset(
    logging.LogRecord("", 0, "", 0, "", (), None).__dict__.keys()
) | {"message", "asctime", "taskName"}


class JsonFormatter(jsonlogger.JsonFormatter):
    """Inject service metadata and request context into each log record."""

    def add_fields(
        self,
        log_record: dict[str, Any],
        record: logging.LogRecord,
        message_dict: dict[str, Any],
    ) -> None:
        super().add_fields(log_record, record, message_dict)

        log_record["timestamp"] = (
            datetime.fromtimestamp(record.created, tz=timezone.utc)
            .isoformat(timespec="milliseconds")
            .replace("+00:00", "Z")
        )
        log_record["level"] = record.levelname
        log_record["logger"] = record.name
        log_record["module"] = record.module
        log_record["service"] = SERVICE_NAME
        log_record["version"] = SERVICE_VERSION

        request_id = request_id_ctx.get()
        if request_id:
            log_record["request_id"] = request_id

        user_id = user_id_ctx.get()
        if user_id is not None:
            log_record["user_id"] = user_id

        # python-json-logger duplicates these under their raw names — drop them
        # so each concept appears exactly once. ``taskName`` is anyio-internal
        # noise added by Python 3.12+ and carries no diagnostic value here.
        for dup in ("levelname", "name", "asctime", "taskName"):
            log_record.pop(dup, None)


def _build_handler() -> logging.Handler:
    """Build the stdout handler used by the JSON logging setup."""
    handler = logging.StreamHandler(sys.stdout)
    # The format string only declares which message field to use; all other
    # keys are produced by JsonFormatter.add_fields above.
    handler.setFormatter(JsonFormatter("%(message)s"))
    return handler


def configure_logging(level: str = "INFO") -> None:
    """Configure the root logger and noisy third-party loggers for JSON."""
    log_level = getattr(logging, level.upper(), logging.INFO)
    handler = _build_handler()

    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(log_level)

    for name in _THIRD_PARTY_LOGGERS:
        third_party = logging.getLogger(name)
        third_party.handlers.clear()
        third_party.propagate = True  # bubble up to the JSON root handler
        # uvicorn.access is very chatty at INFO; keep it but let it inherit.
        third_party.setLevel(log_level)

    logging.captureWarnings(True)


def redact(value: str, *, level: int = logging.INFO, keep: int = 8) -> str:
    """Return a stable hash prefix for sensitive values at non-DEBUG levels.

    Args:
        value: Sensitive string to redact.
        level: Logging level for the call site.
        keep: Number of hexadecimal characters to keep from the digest.

    Returns:
        The original value at DEBUG, otherwise a deterministic hash prefix.
    """
    if logging.getLogger().isEnabledFor(logging.DEBUG) or level <= logging.DEBUG:
        return value
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:keep]}"
