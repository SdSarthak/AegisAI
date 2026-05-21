from datetime import timedelta
from app.core.security import create_access_token
def test_register_success(client):
    response = client.post(
        "/api/v1/auth/register",
        json={
            "email": "test@example.com",
            "password": "testpassword123"
        }
    )

    assert response.status_code == 201


def test_register_duplicate_email(client):
    user_data = {
        "email": "duplicate@example.com",
        "password": "testpassword123"
    }

    client.post(
        "/api/v1/auth/register",
        json=user_data
    )

    response = client.post(
        "/api/v1/auth/register",
        json=user_data
    )

    assert response.status_code == 400
    
def test_login_success(client):
    register_data = {
        "email": "login@example.com",
        "password": "testpassword123"
    }

    client.post(
        "/api/v1/auth/register",
        json=register_data
    )

    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": register_data["email"],
            "password": register_data["password"]
        }
    )

    assert response.status_code == 200

    response_data = response.json()

    assert "access_token" in response_data
    assert response_data["token_type"] == "bearer"
    
def test_login_wrong_password(client):
    register_data = {
        "email": "wrongpass@example.com",
        "password": "correctpassword123"
    }

    client.post(
        "/api/v1/auth/register",
        json=register_data
    )

    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": register_data["email"],
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401
    
def test_invalid_token_returns_401(unauth_client):
    response = unauth_client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": "Bearer invalidtoken"
        }
    )

    assert response.status_code == 401
    
def test_expired_token_returns_401(unauth_client):
    expired_token = create_access_token(
        data={"sub": "expired@example.com"},
        expires_delta=timedelta(minutes=-1)
    )

    response = unauth_client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {expired_token}"
        }
    )

    assert response.status_code == 401
