"""
Tests for CORS Origin check middleware.

Tests create an isolated FastAPI app so they do not depend on the full
application startup (which requires Python >= 3.10).
"""

import pytest
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from app.middleware.origin import OriginCheckMiddleware


@pytest.fixture
def app():
    app = FastAPI()

    @app.get("/health")
    def health():
        return {"status": "healthy"}

    @app.get("/api/v1/auth/csrf-token")
    def csrf_token():
        return {"token": "test-token"}

    @app.post("/badge/verify")
    def badge_verify():
        return {"valid": True}

    @app.get("/protected")
    def protected():
        return {"data": "secret"}

    @app.post("/protected")
    def protected_post():
        return {"data": "created"}

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:5173", "http://localhost:3000"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(OriginCheckMiddleware)

    return app


@pytest.fixture
def client(app):
    return TestClient(app)


class TestOriginCheckMiddleware:
    def test_allowed_origin_passes(self, client):
        """Request with a configured origin (localhost:5173) succeeds."""
        resp = client.get("/health", headers={"Origin": "http://localhost:5173"})
        assert resp.status_code == 200

    def test_missing_origin_is_rejected(self, client):
        """Request without an Origin header is rejected with 403."""
        resp = client.get("/protected")
        assert resp.status_code == 403
        assert "Origin header required" in resp.text

    def test_missing_origin_on_api_endpoint_is_rejected(self, client):
        """API endpoint without Origin header is rejected."""
        resp = client.get("/protected")
        assert resp.status_code == 403

    def test_csrf_token_endpoint_is_exempt(self, client):
        """CSRF token endpoint is exempt from Origin check so frontend can bootstrap."""
        resp = client.get("/api/v1/auth/csrf-token")
        assert resp.status_code == 200

    def test_options_preflight_passes_without_origin(self, client):
        """OPTIONS preflight requests are allowed even without Origin header."""
        resp = client.options(
            "/protected",
            headers={"Access-Control-Request-Method": "GET"},
        )
        assert resp.status_code != 403

    def test_health_endpoint_exempt_without_origin(self, client):
        """Health endpoint is exempt from Origin check."""
        resp = client.get("/health")
        assert resp.status_code == 200

    def test_badge_endpoints_exempt_without_origin(self, client):
        """Badge endpoints are exempt from Origin check."""
        resp = client.post("/badge/verify", json={})
        assert resp.status_code != 403

    def test_allowed_development_origin_succeeds(self, client):
        """Request from localhost:3000 (allowed origin) passes."""
        resp = client.get("/health", headers={"Origin": "http://localhost:3000"})
        assert resp.status_code == 200

    def test_unknown_origin_missing_cors_headers(self, client):
        """Request with an unknown origin gets no CORS headers but passes middleware."""
        resp = client.get("/health", headers={"Origin": "https://evil.com"})
        assert resp.status_code == 200
        assert "access-control-allow-origin" not in resp.headers

    def test_post_without_origin_is_rejected(self, client):
        """POST request without Origin header is rejected."""
        resp = client.post("/protected", json={"key": "value"})
        assert resp.status_code == 403

    def test_post_with_allowed_origin_passes(self, client):
        """POST request with allowed Origin header passes."""
        resp = client.post(
            "/protected",
            json={"key": "value"},
            headers={"Origin": "http://localhost:5173"},
        )
        assert resp.status_code == 200
