"""
CSRF test helpers shared across all test files.

This module defines _CSRFClientWrapper and other utilities needed
for tests that interact with CSRF-protected endpoints.

Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

from fastapi.testclient import TestClient
from typing import Any, Callable, Iterator


class _CSRFClientWrapper:
    """Wrap TestClient to auto-handle CSRF tokens for state-changing requests.

    Auto-injects X-CSRF-Token on POST / PUT / PATCH / DELETE by fetching
    a fresh token from /api/v1/auth/csrf-token on the first such request,
    then caching it for subsequent requests within the same wrapper instance.
    """

    def __init__(self, inner: TestClient) -> None:
        self._inner = inner
        self._csrf_token: str | None = None

    def _ensure_csrf(self) -> None:
        """Fetch and cache a CSRF token if not already cached."""
        if self._csrf_token is None:
            resp = self._inner.get("/api/v1/auth/csrf-token")
            if resp.status_code == 200:
                self._csrf_token = resp.json().get("token", "")

    def _inject_csrf(self, kwargs: dict) -> None:
        """Inject cached CSRF token into request kwargs if not already set."""
        if self._csrf_token is not None and "X-CSRF-Token" not in kwargs.get("headers", {}):
            headers = dict(kwargs.get("headers") or {})
            headers["X-CSRF-Token"] = self._csrf_token
            kwargs["headers"] = headers

    # Explicitly define HTTP verb methods so they always go through the wrapper
    def get(self, url: str, **kwargs: Any) -> Any:
        return self._inner.get(url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> Any:
        self._ensure_csrf()
        self._inject_csrf(kwargs)
        return self._inner.post(url, **kwargs)

    def put(self, url: str, **kwargs: Any) -> Any:
        self._ensure_csrf()
        self._inject_csrf(kwargs)
        return self._inner.put(url, **kwargs)

    def patch(self, url: str, **kwargs: Any) -> Any:
        self._ensure_csrf()
        self._inject_csrf(kwargs)
        return self._inner.patch(url, **kwargs)

    def delete(self, url: str, **kwargs: Any) -> Any:
        self._ensure_csrf()
        self._inject_csrf(kwargs)
        return self._inner.delete(url, **kwargs)

    def request(self, method: str, url: str, **kwargs: Any) -> Any:
        if method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
            self._ensure_csrf()
            self._inject_csrf(kwargs)
        return self._inner.request(method, url, **kwargs)

    def stream(self, method: str, url: str, **kwargs: Any) -> Any:
        if method.upper() in ("POST", "PUT", "PATCH", "DELETE"):
            self._ensure_csrf()
            self._inject_csrf(kwargs)
        return self._inner.stream(method, url, **kwargs)

    def __enter__(self) -> "_CSRFClientWrapper":
        self._inner.__enter__()
        return self

    def __exit__(self, *args: Any) -> None:
        self._inner.__exit__(*args)

    def __enter__(self) -> "_CSRFClientWrapper":
        self._inner.__enter__()
        return self

    def __exit__(self, *args: Any) -> None:
        self._inner.__exit__(*args)
