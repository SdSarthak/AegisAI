from datetime import timedelta
from app.core.security import create_access_token, get_current_user
from app.main import app

# Valid test password that meets all requirements:
# - At least 8 characters
# - At least one uppercase letter
# - At least one digit
# - At least one special character (!@#$%^&*)
VALID_TEST_PASSWORD = "TestPass123!"
ANOTHER_VALID_PASSWORD = "CorrectPass123!"

from jose import jwt
from app.core.config import settings


def test_register_success(client):
    """Test successful registration with valid password."""
    response = client.post(
        "/api/v1/auth/register",
        json={"email": "test@example.com", "password": VALID_TEST_PASSWORD},
    )
    assert response.status_code == 201


def test_register_weak_password(client):
    """Test registration fails with weak password (missing requirements)."""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "weakpass@example.com",
            "password": "weak"  # Too short, no uppercase, no digit, no special char
        }
    )

    # Pydantic validation error
    assert response.status_code == 422
    data = response.json()
    assert "detail" in data
    # Verify it's a validation error
    assert isinstance(data["detail"], list) or "Password must contain" in str(data["detail"])


def test_register_duplicate_email(client):
    """Test registration fails when email already exists."""
    user_data = {
        "email": "duplicate@example.com",
        "password": VALID_TEST_PASSWORD
    }
    client.post("/api/v1/auth/register", json=user_data)
    response = client.post("/api/v1/auth/register", json=user_data)
    assert response.status_code == 400
assert "already registered" in response.json()["detail"]

def test_login_success(client):
    """Test successful login after registration."""
    register_data = {
        "email": "login@example.com",
        "password": VALID_TEST_PASSWORD
    }
    client.post("/api/v1/auth/register", json=register_data)
    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": register_data["email"],
            "password": register_data["password"],
        },
    )
    assert response.status_code == 200
    response_data = response.json()
    assert "access_token" in response_data
    assert response_data["token_type"] == "bearer"


def test_login_wrong_password(client):
    """Test login fails with incorrect password."""
    register_data = {
        "email": "wrongpass@example.com",
        "password": ANOTHER_VALID_PASSWORD
    }
    client.post("/api/v1/auth/register", json=register_data)
    response = client.post(
        "/api/v1/auth/login",
        data={"username": register_data["email"], "password": "wrongpassword"},
    )
    assert response.status_code == 401


def test_invalid_token_returns_401(client):
    # Remove mock auth so real token validation runs
    app.dependency_overrides.pop(get_current_user, None)
    
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": "Bearer invalidtoken"}
    )
    assert response.status_code == 401


def test_expired_token_returns_401(client):
    # Remove mock auth so real token validation runs
    app.dependency_overrides.pop(get_current_user, None)
    
    expired_token = create_access_token(
        data={"sub": "expired@example.com"},
        expires_delta=timedelta(minutes=-1)
    )
    response = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {expired_token}"}
    )
    assert response.status_code == 401


def test_register_full_name_exceeds_max_length(client):
    """Test that full_name exceeding 100 characters returns 422"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": VALID_TEST_PASSWORD,
            "full_name": "a" * 101
        }
    )

    assert response.status_code == 422
    error_detail = response.json()
    assert "full_name" in str(error_detail).lower() or "max" in str(error_detail).lower()


def test_register_company_name_exceeds_max_length(client):
    """Test that company_name exceeding 100 characters returns 422"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": VALID_TEST_PASSWORD,
            "company_name": "a" * 101
        }
    )

    assert response.status_code == 422
    error_detail = response.json()
    assert "company_name" in str(error_detail).lower() or "max" in str(error_detail).lower()


def test_register_with_valid_full_name_length(client):
    """Test that full_name with exactly 100 characters is accepted"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "validname@example.com",
            "password": VALID_TEST_PASSWORD,
            "full_name": "a" * 100
        }
    )

    assert response.status_code == 201


def test_register_with_valid_company_name_length(client):
    """Test that company_name with exactly 100 characters is accepted"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "validcompany@example.com",
            "password": VALID_TEST_PASSWORD,
            "company_name": "a" * 100
        }
    )

    assert response.status_code == 201


def test_register_with_both_fields_at_max_length(client):
    """Test that both full_name and company_name at 100 characters are accepted"""
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "testboth@example.com",
            "password": VALID_TEST_PASSWORD,
            "full_name": "a" * 100,
            "company_name": "b" * 100
        }
    )

    assert response.status_code == 201

