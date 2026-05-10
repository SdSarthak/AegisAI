"""Shared pytest fixtures for all tests."""

import os
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient

# Set test database before importing app
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

from app.core.database import Base, SessionLocal
from app.main import app


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
    
    client = TestClient(app)
    yield client
    
    session.close()
    transaction.rollback()
    connection.close()
    app.dependency_overrides.clear()
