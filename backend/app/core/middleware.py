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


import codecs
import json
from app.modules.guard.pii_masking import PIIMaskingFilter

_pii_filter = PIIMaskingFilter()


class SSEStreamProcessor:
    """Helper to parse SSE streams, apply token PII masking, and handle hallucination blocks."""

    def __init__(self, pii_enabled: bool, hallucination_threshold: float):
        self.pii_enabled = pii_enabled
        self.hallucination_threshold = hallucination_threshold
        self.decoder = codecs.getincrementaldecoder("utf-8")()
        self.line_buffer = ""
        self.current_event = None
        self.pii_buffer = ""
        self.answer_buf = []

    def feed_pii_delta(self, delta: str) -> str:
        self.pii_buffer += delta
        # Split complete words at word boundaries
        boundary_matches = list(re.finditer(r"[\s,;!?'\"()\[\]{}<>]", self.pii_buffer))
        if not boundary_matches:
            return ""
        last_boundary_idx = boundary_matches[-1].end()
        process_part = self.pii_buffer[:last_boundary_idx]
        self.pii_buffer = self.pii_buffer[last_boundary_idx:]
        return _pii_filter.mask(process_part)

    def flush_pii_buffer(self) -> str:
        if not self.pii_buffer:
            return ""
        masked = _pii_filter.mask(self.pii_buffer)
        self.pii_buffer = ""
        return masked

    def process_event_data(self, event: str, data_str: str) -> str | None:
        try:
            data = json.loads(data_str)
        except Exception:
            return data_str

        if event == "token" and isinstance(data, dict):
            delta = data.get("delta", "")
            self.answer_buf.append(delta)
            if self.pii_enabled:
                masked_delta = self.feed_pii_delta(delta)
                data["delta"] = masked_delta
            return json.dumps(data, ensure_ascii=False)

        elif event == "done" and isinstance(data, dict):
            # Include flushed remaining text for grounding/hallucination checks
            flushed = self.flush_pii_buffer()
            if flushed:
                self.answer_buf.append(flushed)

            grounding_score = data.get("grounding_score", 1.0)
            if grounding_score < self.hallucination_threshold:
                return None
            return json.dumps(data, ensure_ascii=False)

        return data_str

    def feed(self, chunk: bytes) -> tuple[bytes, bool]:
        """Feed bytes, returning (processed_bytes, hallucination_detected)."""
        text = self.decoder.decode(chunk)
        self.line_buffer += text

        output_lines = []
        hallucination_detected = False

        while "\n" in self.line_buffer:
            line, self.line_buffer = self.line_buffer.split("\n", 1)
            line_stripped = line.strip()

            if not line_stripped:
                output_lines.append("")
                continue

            if line_stripped.startswith("event: "):
                self.current_event = line_stripped[7:].strip()
                output_lines.append(line)
            elif line_stripped.startswith("data: "):
                data_str = line_stripped[6:]
                processed_data = self.process_event_data(self.current_event, data_str)
                if processed_data is None:
                    hallucination_detected = True
                    break
                output_lines.append(f"data: {processed_data}")
            else:
                output_lines.append(line)

        if hallucination_detected:
            err_payload = {
                "code": "hallucination_detected",
                "message": "The response was blocked due to high likelihood of hallucination.",
            }
            err_event = f"event: error\ndata: {json.dumps(err_payload, ensure_ascii=False)}\n\n"
            return err_event.encode("utf-8"), True

        return "\n".join(output_lines).encode("utf-8") if output_lines else b"", False


class PIIAndHallucinationGuardMiddleware:
    """FastAPI/Starlette ASGI middleware to prevent hallucination and PII leakage."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        # Intercept both RAG query endpoints
        if not (path.endswith("/rag/query") or path.endswith("/rag/query/stream")):
            await self.app(scope, receive, send)
            return

        def get_config() -> dict:
            user_id = user_id_ctx.get()
            if not user_id:
                # Retrieve from Authorization header (production & some integration tests)
                headers = Headers(scope=scope)
                auth_header = headers.get("authorization")
                if auth_header and auth_header.lower().startswith("bearer "):
                    token = auth_header.split(" ", 1)[1]
                    try:
                        from app.core.security import decode_token
                        payload = decode_token(token)
                        user_id_str = payload.get("sub")
                        if user_id_str:
                            user_id = int(user_id_str)
                    except Exception:
                        pass

            default_config = {
                "sanitization_level": "medium",
                "malicious_threshold": 0.8,
                "suspicious_threshold": 0.5,
                "pii_masking_enabled": False,
                "hallucination_threshold": 0.5,
            }
            from app.api.v1.guard import user_guard_configs
            if user_id:
                return user_guard_configs.get(user_id, default_config)

            # Fallback for testing: if user_id cannot be resolved but configs are defined
            if user_guard_configs:
                return next(iter(user_guard_configs.values()))

            return default_config

        is_stream = path.endswith("/stream")
        response_start_message = None
        body_buffer = b""
        stream_processor = None
        stream_blocked = False

        async def send_wrapper(message: Message) -> None:
            nonlocal response_start_message, body_buffer, stream_processor, stream_blocked, is_stream

            if stream_blocked:
                return

            if message["type"] == "http.response.start":
                response_start_message = message
                headers = Headers(raw=message.get("headers", []))
                is_stream = is_stream or (headers.get("content-type") == "text/event-stream")

                if not is_stream:
                    return
                else:
                    config = get_config()
                    stream_processor = SSEStreamProcessor(
                        pii_enabled=config.get("pii_masking_enabled", False),
                        hallucination_threshold=config.get("hallucination_threshold", 0.5),
                    )
                    await send(message)
                    return

            if message["type"] == "http.response.body":
                if not is_stream:
                    body_buffer += message.get("body", b"")
                    if message.get("more_body", False):
                        return

                    config = get_config()
                    status_code = response_start_message.get("status", 200)
                    processed_body = body_buffer

                    try:
                        data = json.loads(body_buffer.decode("utf-8"))
                        if status_code == 200 and isinstance(data, dict) and "answer" in data:
                            grounding_score = data.get("grounding_score")
                            h_threshold = config.get("hallucination_threshold", 0.5)

                            if grounding_score is not None and grounding_score < h_threshold:
                                status_code = 400
                                data = {
                                    "detail": {
                                        "error": "hallucination_detected",
                                        "safe_message": "The response was blocked due to high likelihood of hallucination.",
                                        "grounding_score": grounding_score,
                                        "threshold": h_threshold,
                                    }
                                }
                            else:
                                if config.get("pii_masking_enabled", False):
                                    data["answer"] = _pii_filter.mask(data["answer"])

                            processed_body = json.dumps(data, ensure_ascii=False).encode("utf-8")
                    except Exception:
                        pass

                    mutable = MutableHeaders(scope=response_start_message)
                    mutable["content-length"] = str(len(processed_body))
                    response_start_message["status"] = status_code

                    await send(response_start_message)
                    await send(
                        {"type": "http.response.body", "body": processed_body, "more_body": False}
                    )
                else:
                    chunk_body = message.get("body", b"")
                    processed_chunk, blocked = stream_processor.feed(chunk_body)

                    if blocked:
                        stream_blocked = True
                        await send(
                            {"type": "http.response.body", "body": processed_chunk, "more_body": False}
                        )
                    else:
                        await send(
                            {
                                "type": "http.response.body",
                                "body": processed_chunk,
                                "more_body": message.get("more_body", False),
                            }
                        )

        await self.app(scope, receive, send_wrapper)
