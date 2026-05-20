"""Pytest tests for the bulk import endpoint."""

import pytest
from fastapi.testclient import TestClient
from io import BytesIO
import textwrap
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.main import app
from app.models.user import User

@pytest.fixture(scope="module")
def engine():
    eng = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    Base.metadata.create_all(bind=eng)
    yield eng
    Base.metadata.drop_all(bind=eng)

@pytest.fixture
def db(engine):
    conn = engine.connect()
    tx = conn.begin()
    session = sessionmaker(autocommit=False, autoflush=False, bind=conn)()
    yield session
    session.close()
    tx.rollback()
    conn.close()

@pytest.fixture
def client(db):
    """Create a test client with real database and mocked user."""
    user = User(email="import@test.com", hashed_password="x", full_name="Importer")
    db.add(user)
    db.flush()

    def override_get_db():
        yield db

    def override_user():
        return user

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user] = override_user

    with TestClient(app) as c:
        yield c, db

    app.dependency_overrides.clear()


class TestBulkImport:
    """Tests for POST /api/v1/ai-systems/import endpoint."""

    def test_valid_csv_creates_systems(self, client):
        """Valid CSV creates systems and returns correct created count."""
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
        assert data["created"] == 2
        assert data["errors"] == []

    def test_missing_name_is_skipped(self, client):
        """Row with missing name is skipped and appears in errors."""
        test_client, _ = client

        csv_content = textwrap.dedent("""\
            name,description,use_case,sector,version
            CV Screener,Ranks candidates,CV Screening,HR Tech,1.0
            ,Missing name system,Test,Test,1.0
            Fraud Detector,Flags transactions,Risk Assessment,Finance,2.1
        """).strip().encode("utf-8")

        response = test_client.post(
            "/api/v1/ai-systems/import",
            files={"file": ("test.csv", BytesIO(csv_content), "text/csv")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 2
        assert len(data["errors"]) == 1
        assert data["errors"][0]["row"] == 3
        assert "name is required" in data["errors"][0]["error"]

    def test_duplicate_name_is_reported(self, client):
        """Duplicate name is reported in errors."""
        test_client, db = client

        # Add an existing system
        from app.models.ai_system import AISystem
        user = db.query(User).filter(User.email == "import@test.com").first()
        db.add(AISystem(owner_id=user.id, name="CV Screener"))
        db.commit()

        csv_content = textwrap.dedent("""\
            name,description,use_case,sector,version
            CV Screener,Duplicate name,Risk Assessment,Finance,2.1
        """).strip().encode("utf-8")

        response = test_client.post(
            "/api/v1/ai-systems/import",
            files={"file": ("test.csv", BytesIO(csv_content), "text/csv")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 0
        assert len(data["errors"]) == 1
        assert "duplicate" in data["errors"][0]["error"].lower()

    def test_non_csv_file_returns_400(self, client):
        """Non-CSV file returns 400 status code."""
        test_client, _ = client

        response = test_client.post(
            "/api/v1/ai-systems/import",
            files={"file": ("test.txt", BytesIO(b"not a csv file content"), "text/plain")}
        )

        assert response.status_code == 400
        assert "Invalid CSV" in response.json()["detail"]

    def test_empty_csv_returns_zero_created(self, client):
        """Empty CSV returns 0 created with no errors."""
        test_client, _ = client

        csv_content = b"name,description,use_case,sector,version"

        response = test_client.post(
            "/api/v1/ai-systems/import",
            files={"file": ("test.csv", BytesIO(csv_content), "text/csv")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 0
        assert data["errors"] == []

    def test_multiple_errors_reported(self, client):
        """Multiple errors in different rows are all reported."""
        test_client, db = client

        # Add an existing system for duplicate test
        from app.models.ai_system import AISystem
        user = db.query(User).filter(User.email == "import@test.com").first()
        db.add(AISystem(owner_id=user.id, name="Duplicate Test"))
        db.commit()

        csv_content = textwrap.dedent("""\
            name,description,use_case,sector,version
            ,Missing name 1,Test,Test,1.0
            Duplicate Test,Second occurrence,Test,Test,1.0
        """).strip().encode("utf-8")

        response = test_client.post(
            "/api/v1/ai-systems/import",
            files={"file": ("test.csv", BytesIO(csv_content), "text/csv")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 0
        assert len(data["errors"]) == 2

    def test_response_has_correct_schema(self, client):
        """Response has correct BulkImportResponse schema."""
        test_client, _ = client

        csv_content = textwrap.dedent("""\
            name,description,use_case,sector,version
            Test System,Test description,Test,Test,1.0
        """).strip().encode("utf-8")

        response = test_client.post(
            "/api/v1/ai-systems/import",
            files={"file": ("test.csv", BytesIO(csv_content), "text/csv")}
        )

        assert response.status_code == 200
        data = response.json()
        assert "created" in data
        assert "errors" in data
        assert isinstance(data["created"], int)
        assert isinstance(data["errors"], list)