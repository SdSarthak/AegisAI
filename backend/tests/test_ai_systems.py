import pytest
from fastapi.testclient import TestClient
from app.core.database import get_db
from app.main import app
from app.core.database import Base
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

SQLALCHEMY_DATABASE_URL = "sqlite:///./test.db"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"check_same_thread": False}
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine
)

Base.metadata.create_all(bind=engine)

def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()

app.dependency_overrides[get_db] = override_get_db

client = TestClient(app)

test_user = {
    "email": "test@example.com",
    "password": "test123",
    "full_name": "Test User",
    "company_name": "Test Company"
}

register_response = client.post(
        "/api/v1/auth/register",
        json=test_user
    )

print(register_response.status_code)
print(register_response.json())

login_response = client.post(
    "/api/v1/auth/login",
    headers={"Content-Type": "application/x-www-form-urlencoded"},
    data={
        "username": test_user["email"],
        "password": test_user["password"]
    }
)

print(login_response.status_code)
print(login_response.json())

token = login_response.json()["access_token"]

headers = {
    "Authorization": f"Bearer {token}"
}

def test_create_ai_system():

    response = client.post(
        "/api/v1/ai-systems/",
        json={
            "name": "Test AI",
            "description": "Testing system"
        },
        headers=headers
    )

    assert response.status_code == 201

def test_list_ai_systems():
    response = client.get("/api/v1/ai-systems/", headers=headers)

    assert response.status_code == 200


def test_update_ai_system():
    response = client.put(
        "/api/v1/ai-systems/1",
        json={
            "name": "Updated AI"
        },
        headers=headers
    )

    assert response.status_code == 200


def test_delete_ai_system():
    response = client.delete("/api/v1/ai-systems/1", headers=headers)

    assert response.status_code in [200, 204]


def test_fetch_invalid_ai_system():
    response = client.get("/api/v1/ai-systems/999999", headers=headers)

    assert response.status_code == 404
