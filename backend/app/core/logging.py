"""
Structured JSON logging for the AegisAI backend.

Replaces the scattered ``logging.basicConfig`` calls with a single
configurator that emits one JSON object per log line. Every line carries:

    timestamp   ISO-8601 UTC, e.g. "2026-05-16T09:41:22.481Z"
    level       INFO | WARNING | ERROR | ...
    logger      full dotted logger name  (app.modules.guard.llm_guard)
    module      Python module short name  (llm_guard)
    message     the log message
    request_id  per-request correlation id (when inside a request)
    user_id     authenticated user id (when available)
    service     "aegis-backend"
    version     app version

Any keyword args passed via ``logger.info("msg", extra={...})`` are merged
into the JSON object, so structured fields land as first-class keys and are
queryable as-is by Datadog, Loki, and CloudWatch — no regex grok needed.

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
    """JSON formatter that injects request/service context into every record."""

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
    handler = logging.StreamHandler(sys.stdout)
    # The format string only declares which message field to use; all other
    # keys are produced by JsonFormatter.add_fields above.
    handler.setFormatter(JsonFormatter("%(message)s"))
    return handler


def configure_logging(level: str = "INFO") -> None:
    """
    Configure root + third-party loggers to emit single-line JSON to stdout.

    Idempotent: safe to call more than once (existing handlers are replaced,
    not stacked). Call this once, early, before the app starts serving.
    """
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
    """
    Return ``value`` unchanged at DEBUG, otherwise a stable hash prefix.

    Use this for prompt text / PII before putting it in ``extra=`` so INFO
    logs stay correlatable (same input -> same hash) without leaking content.

        logger.info("guard.scan", extra={"prompt": redact(prompt)})
    """
    if logging.getLogger().isEnabledFor(logging.DEBUG) or level <= logging.DEBUG:
        return value
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()
    return f"sha256:{digest[:keep]}"
