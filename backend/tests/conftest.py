"""Shared pytest fixtures for all tests."""

import os
import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Request, HTTPException, status
from fastapi.testclient import TestClient

# Set test database before importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecret"

from app.core.database import Base, SessionLocal
from app.core.security import decode_token, get_current_user
from app.models.user import SubscriptionTier
from app.main import app
from uuid import uuid4

def _mock_current_user():
    user = MagicMock()
    user.id = 1
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.company_name = "Test Company"
    user.subscription_tier = SubscriptionTier.FREE
    user.is_active = True
    user.is_verified = True
    return user


@pytest.fixture(scope="session")
def db_engine():
    """Create a test database engine."""
    test_db_url = "sqlite:///:memory:"
    engine = create_engine(test_db_url, connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=engine)
    yield engine
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine) -> Session:
    """Create a new database session for each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()
    yield session
    session.close()
    transaction.rollback()
    connection.close()


@pytest.fixture
def client(db_engine):
    """Create test client with test database."""
    from app.core.database import get_db

    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()

    def override_get_db():
        yield session

    def override_current_user(request: Request):
        auth_header = request.headers.get("authorization", "")
        if not auth_header.lower().startswith("bearer "):
            # Block unauthenticated requests!
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Not authenticated"
            )

        token = auth_header.split(" ", 1)[1]
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED, 
                detail="Invalid token"
            )

        from app.models.user import User
        user = session.query(User).filter(User.id == int(user_id)).first()
        return user or _mock_current_user()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    client = TestClient(app)
    yield client

    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()

@pytest.fixture
def auth_headers(client):
    email = f"batch-scan-{uuid4()}@example.com"
    password = "TestPass123!"

    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Batch Scan Test User",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        data={"username": email, "password": password},
    )
    token = response.json()["access_token"]

    return {"Authorization": f"Bearer {token}"}

@pytest.fixture
def other_user_auth_headers(client):
    email = "other@example.com"
    password = "TestPass123!"
    client.post("/api/v1/auth/register", json={"email": email, "password": password, "full_name": "Other User"})
    response = client.post("/api/v1/auth/login", data={"username": email, "password": password})
    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def test_user(db_session) -> MagicMock:
    """Create a mock test user to avoid circular model dependencies."""
    user = MagicMock()
    user.id = 1
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.company_name = "Test Company"
    user.subscription_tier = SubscriptionTier.FREE
    user.is_active = True
    user.is_verified = True
    return user


@pytest.fixture
def other_user(db_session) -> MagicMock:
    """Create another mock test user to avoid circular model dependencies."""
    user = MagicMock()
    user.id = 2
    user.email = "other@example.com"
    user.full_name = "Other User"
    user.company_name = "Other Company"
    user.subscription_tier = SubscriptionTier.FREE
    user.is_active = True
    user.is_verified = True
    return user


@pytest.fixture
def auth_headers(test_user) -> dict:
    """Create authorization headers for a test user."""
    from app.core.security import create_access_token

    token = create_access_token(data={"sub": str(test_user.id)})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def clear_guard_rate_limits():
    """Keep in-memory and Redis guard rate limits isolated between tests."""
    from app.core.rate_limit import guard_scan_rate_limiter
    
    # 1. Clear local memory
    guard_scan_rate_limiter._local_attempts_by_key.clear()
    
    # 2. Clear Redis
    redis_client = guard_scan_rate_limiter._get_redis_client()
    if redis_client is not None:
        redis_client.flushdb()
        
    yield
    
    # Clean up after the test completes
    guard_scan_rate_limiter._local_attempts_by_key.clear()
    if redis_client is not None:
        redis_client.flushdb()
