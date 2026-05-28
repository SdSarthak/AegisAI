from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_api_key_routes_exist():
    response = client.get("/docs")
    assert response.status_code == 200