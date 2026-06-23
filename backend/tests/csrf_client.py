"""CSRF-aware TestClient wrapper for tests that need X-CSRF-Token handling."""

from __future__ import annotations
from typing import Any
from fastapi.testclient import TestClient


class _CSRFClientWrapper:
    """Wrap TestClient to auto-handle CSRF tokens for state-changing requests.
    
    The _csrf_token attribute is stored on this wrapper (not delegated to inner
    TestClient) so that tests can access it via wrapper._csrf_token.
    """

    _CSRF_COOKIE_NAME = "csrf_token"

    def __init__(self, inner: TestClient) -> None:
        self._inner = inner
        # Stored on wrapper for backward compat with auth_headers fixture
        self._csrf_token: str | None = None

    def _ensure_csrf(self) -> None:
        """Fetch a CSRF token if we do not have one yet."""
        if self._csrf_token is None:
            resp = self._inner.get("/api/v1/auth/csrf-token")
            assert resp.status_code == 200, f"CSRF token fetch failed: {resp.status_code}"
            self._csrf_token = resp.json()["token"]
            assert self._csrf_token, "CSRF token is empty"

    def _inject_csrf(self, kwargs: dict) -> None:
        """Add X-CSRF-Token header to state-changing request kwargs."""
        headers = dict(kwargs.get("headers", {}))
        headers["X-CSRF-Token"] = self._csrf_token
        kwargs["headers"] = headers

    def get(self, url: str, **kwargs: object) -> Any:
        return self._inner.get(url, **kwargs)

    def post(self, url: str, **kwargs: object) -> Any:
        self._ensure_csrf()
        self._inject_csrf(kwargs)
        return self._inner.post(url, **kwargs)

    def put(self, url: str, **kwargs: object) -> Any:
        self._ensure_csrf()
        self._inject_csrf(kwargs)
        return self._inner.put(url, **kwargs)

    def patch(self, url: str, **kwargs: object) -> Any:
        self._ensure_csrf()
        self._inject_csrf(kwargs)
        return self._inner.patch(url, **kwargs)

    def delete(self, url: str, **kwargs: object) -> Any:
        self._ensure_csrf()
        self._inject_csrf(kwargs)
        return self._inner.delete(url, **kwargs)

    def request(self, method: str, url: str, **kwargs: object) -> Any:
        if method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
            self._ensure_csrf()
            self._inject_csrf(kwargs)
        return self._inner.request(method, url, **kwargs)

    def __getattr__(self, name: str) -> object:
        return getattr(self._inner, name)
