"""Shared pytest fixtures for all tests."""

import os
import pytest
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Set test database before importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.core.database import Base, SessionLocal
from app.main import app
from app.models.user import User, SubscriptionTier


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
    
    app.dependency_overrides[get_db] = override_get_db

    # Mock authenticated user
    from app.core.security import get_current_user
    from unittest.mock import MagicMock

    def override_get_current_user():
        user = MagicMock(spec=User)
        user.id = 1  # Integer, not string
        user.email = "test@example.com"
        user.full_name = "Test User"
        user.company_name = "Test Company"
        user.subscription_tier = SubscriptionTier.FREE
        user.is_active = True
        user.is_verified = False
        user.created_at = datetime.utcnow()
        return user

    app.dependency_overrides[get_current_user] = override_get_current_user
    
    yield TestClient(app)
    
    # Cleanup
    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()


@pytest.fixture
def unauth_client(db_engine):
    """Create test client without auth overrides - for testing auth failures."""
    from app.core.database import get_db
    from app.core.security import get_current_user
    
    # Clear ALL existing overrides first to ensure clean state
    app.dependency_overrides.clear()
    
    connection = db_engine.connect()
    transaction = connection.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=connection)()
    
    def override_get_db():
        yield session
    
    app.dependency_overrides[get_db] = override_get_db
    # Explicitly do NOT override get_current_user - let it use the real implementation
    
    yield TestClient(app)
    
    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()
