"""Pytest tests for the bulk import endpoint."""

import pytest
import os
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from io import BytesIO
import textwrap
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.user import User

# Use a physical file for tests to support multi-threaded access (BackgroundTasks)
TEST_DB_PATH = "test_aegisai_clean.db"

@pytest.fixture(scope="module")
def engine():
    if os.path.exists(TEST_DB_PATH):
        os.remove(TEST_DB_PATH)
    
    eng = create_engine(f"sqlite:///{TEST_DB_PATH}", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)
    
    if os.path.exists(TEST_DB_PATH):
        try:
            os.remove(TEST_DB_PATH)
        except PermissionError:
            pass

@pytest.fixture
def db(engine):
    session = sessionmaker(autocommit=False, autoflush=False, bind=engine)()
    yield session
    # Cleanup data between tests
    for table in reversed(Base.metadata.sorted_tables):
        session.execute(table.delete())
    session.commit()
    session.close()

@pytest.fixture
def client(db):
    """Create a test client with real database and mocked user."""
    user = User(email="import@test.com", hashed_password="x", full_name="Importer")
    db.add(user)
    db.commit()
    db.refresh(user)

    def override_get_db():
        yield db

    def override_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_user

    # IMPORTANT: Since BackgroundTasks use the REAL SessionLocal in production,
    # and our _process_import_task imports it directly, we need to mock SessionLocal
    # to point to our test engine during tests.
    
    with patch("app.core.database.SessionLocal", return_value=db):
        with TestClient(app) as c:
            yield c, db

    app.dependency_overrides.clear()


class TestBulkImport:
    """Tests for POST /api/v1/ai-systems/import endpoint."""

    def test_valid_csv_initiates_background_import(self, client):
        """Valid CSV initiates background import and returns async message."""
        test_client, _ = client

        csv_content = textwrap.dedent("""\
            name,description,use_case,sector,version
            CV Screener,Ranks candidates by CV content,CV Screening,HR Tech,1.0
            Fraud Detector,Flags anomalous transactions,Risk Assessment,Finance,2.1
        """).strip().encode("utf-8")

        response = test_client.post(
            "/api/v1/ai-systems/import",
            files={"file": ("test.csv", BytesIO(csv_content), "text/csv")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 0
        assert "started in the background" in data["message"]

    def test_missing_name_returns_async_message(self, client):
        """Even with potential errors, the import starts in background."""
        test_client, _ = client

        csv_content = textwrap.dedent("""\
            name,description,use_case,sector,version
            CV Screener,Ranks candidates,CV Screening,HR Tech,1.0
            ,Missing name system,Test,Test,1.0
        """).strip().encode("utf-8")

        response = test_client.post(
            "/api/v1/ai-systems/import",
            files={"file": ("test.csv", BytesIO(csv_content), "text/csv")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 0
        assert "started in the background" in data["message"]

    def test_non_csv_file_returns_400(self, client):
        """Non-CSV file returns 400 status code early."""
        test_client, _ = client

        response = test_client.post(
            "/api/v1/ai-systems/import",
            files={"file": ("test.txt", BytesIO(b"not a csv file content"), "text/plain")}
        )

        assert response.status_code == 400
        assert "Invalid CSV" in response.json()["detail"]

    def test_large_file_returns_413(self, client):
        """Large file exceeds limit and returns 413 early."""
        test_client, _ = client
        
        # Create a content larger than 10MB (settings default)
        large_content = b"a" * (11 * 1024 * 1024)

        response = test_client.post(
            "/api/v1/ai-systems/import",
            files={"file": ("large.csv", BytesIO(large_content), "text/csv")}
        )

        assert response.status_code == 413
        assert "File too large" in response.json()["detail"]

    def test_missing_header_returns_400(self, client):
        """CSV without 'name' header returns 400 early."""
        test_client, _ = client

        csv_content = b"desc,version\nSystem,1.0"

        response = test_client.post(
            "/api/v1/ai-systems/import",
            files={"file": ("test.csv", BytesIO(csv_content), "text/csv")}
        )

        assert response.status_code == 400
        assert "name" in response.json()["detail"]

    def test_response_has_correct_schema(self, client):
        """Response has correct BulkImportResponse schema."""
        test_client, _ = client

        csv_content = b"name\nTest System"

        response = test_client.post(
            "/api/v1/ai-systems/import",
            files={"file": ("test.csv", BytesIO(csv_content), "text/csv")}
        )

        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        assert "created" in data
        assert "errors" in data
