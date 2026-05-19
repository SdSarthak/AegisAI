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
    Provides a DB session that shares the single StaticPool connection.
 
    We do NOT wrap in a transaction+rollback here because the RAG
    integration test needs commits from one request to be visible to
    the next request within the same test.  Each test still gets a
    fresh state because Base.metadata.drop_all / create_all runs
    between tests via the autouse fixture below.
    """
    session = TestingSessionLocal()
    try:
        yield session
    finally:
        session.close()
 
 
@pytest.fixture(autouse=True)
def reset_db():
    """
    Drop and recreate all tables before every test so each test starts
    with a clean database regardless of what the previous test committed.
    """
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
 
 
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