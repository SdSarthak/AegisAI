"""
Tests for root and health endpoints.
"""
from unittest.mock import patch
from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from app.main import app

client = TestClient(app)


def test_root_returns_expected_keys():
    response = client.get("/")
    assert response.status_code == 200
    data = response.json()
    assert data["project"] == "AegisAI"
    assert "version" in data
    assert "docs" in data
    assert "modules" in data


def test_root_modules_are_correct():
    response = client.get("/")
    data = response.json()
    assert set(data["modules"]) == {"compliance", "guard", "rag"}


def test_health_when_db_is_up():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["database"] == "connected"
    assert data["service"] == "AegisAI Backend"
    assert "version" in data


def test_health_when_db_is_down():
    with patch("app.main.engine") as mock_engine:
        mock_engine.connect.side_effect = OperationalError(
            "connection refused", {}, None
        )
        response = client.get("/health")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "degraded"
    assert data["database"] == "disconnected"