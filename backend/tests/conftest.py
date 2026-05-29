"""Shared pytest fixtures for all tests."""

import os
import pytest
from unittest.mock import MagicMock
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Header
from fastapi.testclient import TestClient

# Set test database before importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"
os.environ["SECRET_KEY"] = "testsecret"
os.environ["REDIS_URL"] = ""

from app.core.database import Base, SessionLocal
from app.core.security import decode_token, get_current_user
from app.models.user import SubscriptionTier, User
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
    from app.core.rate_limit import guard_scan_rate_limiter

    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()
    guard_scan_rate_limiter._local_attempts_by_key.clear()

    def override_get_db():
        yield session

    def override_current_user(authorization: str | None = Header(default=None)):
        if authorization and authorization.lower().startswith("bearer "):
            token = authorization.split(" ", 1)[1]
            payload = decode_token(token)
            user_id = int(payload["sub"])
            user = session.query(User).filter(User.id == user_id).first()
            if user is not None:
                return user
        return _mock_current_user()

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_current_user

    client = TestClient(app)
    yield client

    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()
