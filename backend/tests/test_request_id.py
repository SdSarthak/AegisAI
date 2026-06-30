"""
Tests for the request ID tracing middleware and context helpers.

The RequestContextMiddleware is tested through the full FastAPI stack
(TestClient) to verify:
  * X-Request-ID header is generated when missing and echoed back
  * Client-supplied X-Request-ID is honoured verbatim
  * Unsafe characters in the client-supplied header are rejected
  * The request_id_ctx ContextVar is populated during request handling
  * The get_request_id() helper returns the correct id
  * Concurrent requests receive distinct ids
"""

import logging
import threading
import time

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.context import get_request_id, request_id_ctx
from app.core.logging import configure_logging
from app.core.middleware import RequestContextMiddleware


def _make_app() -> FastAPI:
    app = FastAPI()
    app.add_middleware(RequestContextMiddleware)
    return app


def test_get_request_id_returns_none_outside_request():
    """Outside any request the ContextVar is None."""
    assert get_request_id() is None
    # Confirm the raw ContextVar also has no value
    assert request_id_ctx.get() is None


def test_request_id_generated_when_missing(app_with_middleware):
    client = TestClient(app_with_middleware)
    resp = client.get("/ping")
    assert resp.status_code == 200
    assert resp.headers.get("x-request-id")
    assert len(resp.headers["x-request-id"]) == 32  # uuid4 hex length


def test_request_id_honoured_when_provided(app_with_middleware):
    client = TestClient(app_with_middleware)
    resp = client.get("/ping", headers={"X-Request-ID": "abcd1234efgh5678"})
    assert resp.status_code == 200
    assert resp.headers.get("x-request-id") == "abcd1234efgh5678"


def test_request_id_with_uuid_format(app_with_middleware):
    client = TestClient(app_with_middleware)
    import uuid
    uid = str(uuid.uuid4())
    resp = client.get("/ping", headers={"X-Request-ID": uid})
    assert resp.status_code == 200
    assert resp.headers.get("x-request-id") == uid


def test_malicious_request_id_rejected(app_with_middleware):
    """Injection characters in X-Request-ID are stripped, not echoed."""
    client = TestClient(app_with_middleware)
    resp = client.get("/ping", headers={"X-Request-ID": "safe\x00null\rinjection"})
    assert resp.status_code == 200
    returned = resp.headers.get("x-request-id") or ""
    assert "\x00" not in returned
    assert "\n" not in returned
    assert "\r" not in returned
    assert "safe" in returned or len(returned) == 32


def test_get_request_id_in_route_handler(app_with_middleware):
    """A route can read the current request id via get_request_id()."""
    client = TestClient(app_with_middleware)
    resp = client.get("/get-request-id")
    assert resp.status_code == 200
    body = resp.json()
    assert body["request_id"] is not None
    assert len(body["request_id"]) == 32


def test_concurrent_requests_get_different_ids(app_with_middleware):
    """Two simultaneous requests must not share a request id."""
    results: dict[int, str] = {}
    errors: dict[int, Exception] = {}

    def make_request(idx: int) -> None:
        try:
            client = TestClient(app_with_middleware)
            resp = client.get("/ping")
            results[idx] = resp.headers.get("x-request-id", "")
        except Exception as exc:
            errors[idx] = exc

    threads = [threading.Thread(target=make_request, args=(i,)) for i in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert not errors, errors
    ids = list(results.values())
    assert len(set(ids)) == len(ids), f"Duplicate request IDs found: {ids}"


def test_request_id_ctx_isolation(app_with_middleware):
    """request_id_ctx must not leak between requests."""
    client = TestClient(app_with_middleware)
    ids = []
    for _ in range(5):
        resp = client.get("/ping")
        ids.append(resp.headers.get("x-request-id"))
    assert len(set(ids)) == 5, "request_id_ctx leaked between requests"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def app_with_middleware():
    configure_logging(level="CRITICAL")
    app = _make_app()

    @app.get("/ping")
    def ping():
        return {"ok": True}

    @app.get("/get-request-id")
    def get_req_id():
        return {"request_id": get_request_id()}

    return app