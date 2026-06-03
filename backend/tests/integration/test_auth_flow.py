from fastapi.testclient import TestClient


def test_complete_auth_flow(client: TestClient):
    register_data = {
        "email": "flow@example.com",
        "password": "FlowTest123!",
        "full_name": "Flow User",
        "company_name": "Flow Corp"
    }
    register_response = client.post("/api/v1/auth/register", json=register_data)
    assert register_response.status_code == 201

    login_response = client.post(
        "/api/v1/auth/login",
        data={"username": register_data["email"], "password": register_data["password"]}
    )
    assert login_response.status_code == 200
    token = login_response.json()["access_token"]

    me_response = client.get("/api/v1/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_response.status_code == 200
    assert me_response.json()["email"] == register_data["email"]


def test_auth_me_without_token(client: TestClient):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_auth_me_with_tampered_token(client: TestClient):
    assert client.get("/api/v1/auth/me", headers={"Authorization": "Bearer invalidtoken"}).status_code == 401
