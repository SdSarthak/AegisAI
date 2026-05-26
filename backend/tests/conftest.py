"""Shared pytest fixtures for all tests."""

import os
import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Request
from fastapi.testclient import TestClient

# Set required env vars before importing app
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key-for-ci")

from app.core.database import Base, SessionLocal
from app.core.security import decode_token, get_current_user
from app.models.user import SubscriptionTier
from app.models.user import User
from app.main import app


def _mock_current_user():
    user = MagicMock()
    user.id = 1                                # ✅ integer
    user.email = "test@example.com"
    user.full_name = "Test User"               # ✅ string
    user.company_name = "Test Company"
    user.subscription_tier = SubscriptionTier.FREE  # ✅ proper enum
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
            return _mock_current_user()

        token = auth_header.split(" ", 1)[1]
        payload = decode_token(token)
        user_id = payload.get("sub")
        if user_id is None:
            return _mock_current_user()

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
def unauthenticated_client(db_engine):
    """Create test client that does NOT mock authentication.

    Use this fixture to verify that endpoints correctly reject requests
    without a valid JWT token (expecting 401 / 403 responses).
    """
    from app.core.database import get_db

    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()

    def override_get_db():
        yield session

    app.dependency_overrides[get_db] = override_get_db
    # Deliberately NOT overriding get_current_user

    client = TestClient(app)
    yield client

    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()


@pytest.fixture(autouse=True)
def clear_guard_rate_limits():
    """Keep in-memory guard rate limits isolated between tests."""
    from app.core.rate_limit import guard_scan_rate_limiter

    guard_scan_rate_limiter._local_attempts_by_key.clear()
    yield
    guard_scan_rate_limiter._local_attempts_by_key.clear()
