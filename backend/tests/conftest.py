"""Shared pytest fixtures for all tests."""

import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

# -------------------------------------------------------------------
# Set test database before importing app
# -------------------------------------------------------------------

os.environ["DATABASE_URL"] = "sqlite://"

# -------------------------------------------------------------------
# Import database module first
# -------------------------------------------------------------------

from app.core import database
from app.core.database import Base

# Import ALL models before create_all
import app.models

# -------------------------------------------------------------------
# Shared in-memory SQLite engine
# -------------------------------------------------------------------

TEST_DATABASE_URL = "sqlite://"

engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
)

# IMPORTANT:
# Override global app DB engine/session BEFORE app import
database.engine = engine
database.SessionLocal = TestingSessionLocal

# -------------------------------------------------------------------
# Create tables once
# -------------------------------------------------------------------

Base.metadata.create_all(bind=engine)

# -------------------------------------------------------------------
# Import app AFTER overriding engine/session
# -------------------------------------------------------------------

from app.main import app

# -------------------------------------------------------------------
# Database session fixture
# -------------------------------------------------------------------

@pytest.fixture
def db_session() -> Session:
    """
    Create isolated DB session per test.
    """

    connection = engine.connect()
    transaction = connection.begin()

    session = TestingSessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()

# -------------------------------------------------------------------
# FastAPI test client fixture
# -------------------------------------------------------------------

@pytest.fixture
def client(db_session):
    """
    Create FastAPI test client with overridden DB dependency.
    """

    from app.core.database import get_db

    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db

    with TestClient(app) as test_client:
        yield test_client

    app.dependency_overrides.clear()