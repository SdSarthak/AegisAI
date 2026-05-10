import pytest
from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_create_ai_system():
    response = client.post(
        "/api/v1/ai-systems/",
        json={
            "name": "Test AI",
            "description": "Testing system"
        }
    )

    assert response.status_code in [200, 201, 401]


def test_list_ai_systems():
    response = client.get("/api/v1/ai-systems/")

    assert response.status_code in [200, 401]


def test_update_ai_system():
    response = client.put(
        "/api/v1/ai-systems/1",
        json={
            "name": "Updated AI"
        }
    )

    assert response.status_code in [200, 404, 401]


def test_delete_ai_system():
    response = client.delete("/api/v1/ai-systems/1")

    assert response.status_code in [200, 204, 404, 401]


def test_fetch_invalid_ai_system():
    response = client.get("/api/v1/ai-systems/999999")

    assert response.status_code in [404, 401]