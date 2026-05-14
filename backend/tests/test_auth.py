"""Pytest tests for authentication endpoints (register, login, protected routes)."""

import pytest
from datetime import timedelta

from app.core.security import create_access_token


# ---------------------------------------------------------------------------
# Registration tests
# ---------------------------------------------------------------------------


class TestRegistration:
    """Tests for POST /api/v1/auth/register"""

    def setup_method(self):
        """Shared test data used by every test in this class."""
        self.payload = {
            "email": "newuser@example.com",
            "password": "Secret123!",
            "full_name": "Test User",
            "company_name": "Test Co",
        }

    def test_register_success_returns_201(self, client):
        """Registering a brand-new user should return HTTP 201."""
        response = client.post("/api/v1/auth/register", json=self.payload)
        assert response.status_code == 201

    def test_register_response_has_email(self, client):
        """The response body should contain the registered email."""
        response = client.post("/api/v1/auth/register", json=self.payload)
        assert response.json()["email"] == self.payload["email"]

    def test_register_duplicate_email_returns_400(self, client):
        """Registering the same email twice should return HTTP 400."""
        # First registration — should succeed
        client.post("/api/v1/auth/register", json=self.payload)

        # Second registration with the same email — should fail
        response = client.post("/api/v1/auth/register", json=self.payload)
        assert response.status_code == 400

    def test_register_duplicate_email_error_message(self, client):
        """The 400 response should say the email is already registered."""
        client.post("/api/v1/auth/register", json=self.payload)
        response = client.post("/api/v1/auth/register", json=self.payload)
        assert response.json()["detail"] == "Email already registered"


# ---------------------------------------------------------------------------
# Login tests
# ---------------------------------------------------------------------------


class TestLogin:
    """Tests for POST /api/v1/auth/login"""

    def setup_method(self):
        """Shared register + login data used by every test in this class."""
        self.register_payload = {
            "email": "loginuser@example.com",
            "password": "Secret123!",
            "full_name": "Login User",
        }
        # NOTE: The login endpoint uses OAuth2PasswordRequestForm.
        # That form reads "username" (not "email") and expects form data,
        # so we use data={} here instead of json={}.
        self.login_form = {
            "username": "loginuser@example.com",
            "password": "Secret123!",
        }

    def test_login_correct_credentials_returns_jwt(self, client):
        """Logging in with the correct password should return an access token."""
        # First, register the user
        client.post("/api/v1/auth/register", json=self.register_payload)

        # Then log in
        response = client.post("/api/v1/auth/login", data=self.login_form)

        assert response.status_code == 200
        body = response.json()
        assert "access_token" in body
        assert body["token_type"] == "bearer"
        assert len(body["access_token"]) > 0

    def test_login_wrong_password_returns_401(self, client):
        """Logging in with the wrong password should return HTTP 401."""
        # Register the user
        client.post("/api/v1/auth/register", json=self.register_payload)

        # Try to log in with a wrong password
        wrong_form = {"username": "loginuser@example.com", "password": "WrongPass999!"}
        response = client.post("/api/v1/auth/login", data=wrong_form)

        assert response.status_code == 401

    def test_login_wrong_password_error_message(self, client):
        """The 401 response should say the credentials are incorrect."""
        client.post("/api/v1/auth/register", json=self.register_payload)
        wrong_form = {"username": "loginuser@example.com", "password": "WrongPass999!"}
        response = client.post("/api/v1/auth/login", data=wrong_form)

        assert response.json()["detail"] == "Incorrect email or password"


# ---------------------------------------------------------------------------
# Protected route tests  (GET /api/v1/auth/me)
# ---------------------------------------------------------------------------


class TestProtectedRoute:
    """Tests for token validation on a protected endpoint."""

    def test_expired_token_returns_401(self, client):
        """Using a token that has already expired should return HTTP 401.

        We create a real JWT but set its expiry in the past (-1 second),
        so the app will reject it as expired.
        """
        expired_token = create_access_token(
            data={"sub": "999"},
            expires_delta=timedelta(seconds=-1),  # already expired!
        )

        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )

        assert response.status_code == 401

    def test_invalid_token_returns_401(self, client):
        """Sending a completely made-up token string should return HTTP 401.

        The app tries to decode it, fails, and returns 401.
        """
        response = client.get(
            "/api/v1/auth/me",
            headers={"Authorization": "Bearer this.is.not.a.real.token"},
        )

        assert response.status_code == 401

    def test_missing_token_returns_401(self, client):
        """Calling a protected route with no token at all should return HTTP 401."""
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 401
