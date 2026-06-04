"""Shared pytest fixtures for all tests."""

import os
from unittest.mock import MagicMock
from uuid import uuid4

import pytest
from fastapi import HTTPException, Request, status
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("ALGORITHM", "HS256")
os.environ.setdefault("ACCESS_TOKEN_EXPIRE_MINUTES", "30")

from app.core.database import Base
from app.core.security import decode_token, get_current_user
from app.main import app
from app.models.user import SubscriptionTier, User


def _mock_current_user(user_id: int = 1):
    """Return a mock authenticated user."""
    user = MagicMock()
    user.id = user_id
    user.email = f"test{user_id}@example.com"
    user.full_name = "Test User"
    user.company_name = "Test Company"
    user.subscription_tier = SubscriptionTier.FREE
    user.is_active = True
    user.is_verified = True
    return user


@pytest.fixture(scope="session")
def db_engine():
    """Create a test database engine."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)

    yield engine

    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db_session(db_engine) -> Session:
    """Create a database session for each test."""
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection,
    )()

    try:
        yield session
    finally:
        session.close()
        transaction.rollback()
        connection.close()


@pytest.fixture
def client(db_engine):
    """Create a test client with isolated DB session."""
    from app.core.database import get_db

    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(
        autocommit=False,
        autoflush=False,
        bind=connection,
    )()

    def override_get_db():
        yield session

    def override_current_user(request: Request):
        auth_header = request.headers.get("authorization", "")

        if not auth_header.lower().startswith("bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )

        token = auth_header.split(" ", 1)[1]
        payload = decode_token(token)
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authentication credentials",
            )

        user_id = int(user_id)
        user = session.query(User).filter(User.id == user_id).first()

        return user or _mock_current_user(user_id)

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    try:
        yield TestClient(app)
    finally:
        session.close()
        transaction.rollback()
        connection.close()
        app.dependency_overrides.clear()


@pytest.fixture
def auth_headers(client):
    """Create auth headers for a test user."""
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
        data={
            "username": email,
            "password": password,
        },
    )

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture
def other_user_auth_headers(client):
    """Create auth headers for another user."""
    email = f"other-{uuid4()}@example.com"
    password = "OtherPass123!"

    client.post(
        "/api/v1/auth/register",
        json={
            "email": email,
            "password": password,
            "full_name": "Other User",
            "company_name": "Other Corp",
        },
    )

    response = client.post(
        "/api/v1/auth/login",
        data={
            "username": email,
            "password": password,
        },
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )

    token = response.json()["access_token"]
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def clear_guard_rate_limits():
    """Keep in-memory and Redis guard rate limits isolated between tests."""
    from app.core.rate_limit import guard_scan_rate_limiter

    guard_scan_rate_limiter._local_attempts_by_key.clear()

    redis_client = guard_scan_rate_limiter._get_redis_client()
    if redis_client is not None:
        redis_client.flushdb()

    yield

    guard_scan_rate_limiter._local_attempts_by_key.clear()
    if redis_client is not None:
        redis_client.flushdb()