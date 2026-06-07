from fastapi.testclient import TestClient


def test_complete_auth_flow(client: TestClient):
    
    # Step 1: Register user
    register_data = {
        "email": "flow@example.com",
        "password": "TestPass123!"
    }

    register_response = client.post(
        "/api/v1/auth/register",
        json=register_data
    )

    assert register_response.status_code == 201

    # Step 2: Login user
    login_response = client.post(
        "/api/v1/auth/login",
        data={
            "username": register_data["email"],
            "password": register_data["password"]
        }
    )

    assert login_response.status_code == 200

    login_data = login_response.json()

    assert "access_token" in login_data

    token = login_data["access_token"]

    # Step 3: Access protected route with valid token
    me_response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": f"Bearer {token}"
        }
    )

    assert me_response.status_code == 200

    me_data = me_response.json()

    assert me_data["email"] == register_data["email"]


def test_auth_me_without_token(client: TestClient):
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401


def test_auth_me_with_tampered_token(client: TestClient):
    response = client.get(
        "/api/v1/auth/me",
        headers={
            "Authorization": "Bearer invalidtoken"
        }
    )

    assert response.status_code == 401
