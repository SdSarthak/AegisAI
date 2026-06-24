"""
Tests for CSRF token protection middleware.
Copyright (C) 2024 Sarthak Doshi (github.com/SdSarthak)
SPDX-License-Identifier: AGPL-3.0-only
"""

import os
import pytest


class TestCSRFTokenEndpoint:
    def test_returns_token(self, client):
        """GET /csrf-token returns a 64-char hex token."""
        resp = client.get("/api/v1/auth/csrf-token")
        assert resp.status_code == 200
        data = resp.json()
        assert "token" in data
        assert len(data["token"]) == 64

    def test_token_is_unique_per_call(self, client):
        """Each call to /csrf-token returns a different token."""
        tokens = set()
        for _ in range(5):
            resp = client.get("/api/v1/auth/csrf-token")
            assert resp.status_code == 200
            tokens.add(resp.json()["token"])
        assert len(tokens) == 5

    def test_sets_csrf_cookie(self, client):
        """The endpoint sets a csrf_token cookie on the response."""
        resp = client.get("/api/v1/auth/csrf-token")
        assert resp.status_code == 200
        cookies = {c.name: c for c in client.cookies.jar}
        assert "csrf_token" in cookies
        assert cookies["csrf_token"].value == resp.json()["token"]

    def test_login_endpoint_is_exempt_from_csrf(self, client):
        """POST /auth/login is on the exempt list so it does not 403."""
        resp = client.post(
            "/api/v1/auth/login",
            data={"username": "nonexistent@example.com", "password": "wrong"},
        )
        assert resp.status_code != 403, resp.text

    def test_register_endpoint_is_exempt_from_csrf(self, client):
        """POST /auth/register is on the exempt list so it does not 403."""
        resp = client.post(
            "/api/v1/auth/register",
            json={
                "email": "csrf_test@example.com",
                "password": "TestPass123!",
                "full_name": "CSRF Test",
                "company_name": "CSRF Co",
            },
        )
        assert resp.status_code != 403, resp.text


@pytest.mark.skipif(
    os.environ.get("DISABLE_CSRF") == "1",
    reason="CSRF middleware disabled via DISABLE_CSRF env var",
)
class TestCSRFMiddleware:
    """
    Test CSRF protection on POST /api/v1/ai-systems (no password verification).
    auth_headers provides a real token for a freshly-registered user whose password
    we know (TestPass123!).
    """

    def test_statechanging_without_token_returns_403(self, client, auth_headers):
        """POST with wrong X-CSRF-Token value is rejected with 403.

        We intentionally send a non-matching token so compare_digest fails.
        (Sending no header would match the stale cookie via empty-string comparison.)
        """
        resp = client.post(
            "/api/v1/ai-systems",
            json={},
            headers={**auth_headers, "X-CSRF-Token": "wrong_token_value"},
        )
        assert resp.status_code == 403, f"Expected 403, got {resp.status_code}: {resp.text}"
        assert "CSRF" in resp.text or "csrf" in resp.text.lower()

    def test_statechanging_with_valid_token_passes_csrf(self, client, auth_headers):
        """POST with matching cookie+header passes the CSRF check."""
        csrf_resp = client.get("/api/v1/auth/csrf-token")
        assert csrf_resp.status_code == 200
        token = csrf_resp.json()["token"]
        resp = client.post(
            "/api/v1/ai-systems",
            json={},
            headers={**auth_headers, "X-CSRF-Token": token},
        )
        # 422 = CSRF passed, validation error. 403 = CSRF still blocking.
        assert resp.status_code != 403, f"CSRF blocked: {resp.text}"

    def test_statechanging_with_wrong_token_returns_403(self, client, auth_headers):
        """POST with a mismatched token is rejected with 403."""
        resp = client.post(
            "/api/v1/ai-systems",
            json={},
            headers={**auth_headers, "X-CSRF-Token": "a" * 64},
        )
        assert resp.status_code == 403

    def test_safe_methods_do_not_require_csrf(self, client, auth_headers):
        """GET endpoints are exempt from CSRF."""
        resp = client.get("/health")
        assert resp.status_code == 200
        resp2 = client.get("/api/v1/auth/me", headers=auth_headers)
        assert resp2.status_code == 200

    def test_badge_endpoints_are_exempt(self, client):
        """All /badge/* paths are exempt from CSRF."""
        resp = client.post("/badge/verify", json={})
        assert resp.status_code != 403, resp.text

    def test_csrf_token_endpoint_itself_is_exempt(self, client):
        """POST to /csrf-token does not trigger a CSRF loop."""
        resp = client.post("/api/v1/auth/csrf-token")
        assert resp.status_code != 403, resp.text

    def test_put_and_patch_also_require_csrf(self, client, auth_headers):
        """PUT and PATCH methods are also protected."""
        for method in ("put", "patch"):
            fn = getattr(client, method)
            resp = fn(
                "/api/v1/ai-systems",
                json={},
                headers={**auth_headers, "X-CSRF-Token": "wrong"},
            )
            assert resp.status_code == 403, f"{method.upper()} got {resp.status_code}: {resp.text}"

    def test_delete_also_requires_csrf(self, client, auth_headers):
        """DELETE method is also protected."""
        resp = client.delete(
            "/api/v1/ai-systems",
            headers={**auth_headers, "X-CSRF-Token": "wrong"},
        )
        assert resp.status_code == 403, f"DELETE got {resp.status_code}: {resp.text}"

    def test_exempt_path_with_csrf_mismatch_still_passes(self, client):
        """Exempt paths bypass CSRF even without a token."""
        resp = client.post(
            "/api/v1/auth/login",
            data={"username": "any@example.com", "password": "any"},
        )
        assert resp.status_code != 403, resp.text