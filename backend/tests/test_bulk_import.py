"""Pytest tests for the bulk import endpoint."""

import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
from io import BytesIO
import textwrap


@pytest.fixture
def client():
    """Create a test client with mocked dependencies."""
    with patch("app.core.database.get_db") as mock_db:
        mock_session = MagicMock()
        mock_db.return_value = mock_session

        from app.main import app
        from app.core.security import get_current_user

        mock_user = MagicMock()
        mock_user.id = 1

        app.dependency_overrides[get_current_user] = lambda: mock_user

        with TestClient(app) as client:
            yield client, mock_session

        app.dependency_overrides.clear()


class TestBulkImport:
    """Tests for POST /api/v1/ai-systems/import endpoint."""

    def test_valid_csv_creates_systems(self, client):
        """Valid CSV creates systems and returns correct created count."""
        test_client, mock_session = client

        csv_content = textwrap.dedent("""\
            name,description,use_case,sector,version
            CV Screener,Ranks candidates by CV content,CV Screening,HR Tech,1.0
            Fraud Detector,Flags anomalous transactions,Risk Assessment,Finance,2.1
        """).strip().encode("utf-8")

        mock_session.query.return_value.filter.return_value.first.return_value = None

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
        test_client, mock_session = client

        csv_content = textwrap.dedent("""\
            name,description,use_case,sector,version
            CV Screener,Ranks candidates,CV Screening,HR Tech,1.0
            ,Missing name system,Test,Test,1.0
            Fraud Detector,Flags transactions,Risk Assessment,Finance,2.1
        """).strip().encode("utf-8")

        def mock_filter(*args, **kwargs):
            mock_query = MagicMock()
            mock_query.first.return_value = None
            return mock_query

        mock_session.query.return_value.filter.side_effect = mock_filter

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
        test_client, mock_session = client

        csv_content = textwrap.dedent("""\
            name,description,use_case,sector,version
            CV Screener,Ranks candidates,CV Screening,HR Tech,1.0
            CV Screener,Duplicate name,Risk Assessment,Finance,2.1
        """).strip().encode("utf-8")

        def mock_filter(*args, **kwargs):
            mock_query = MagicMock()
            existing = MagicMock() if "CV Screener" in str(args) else None
            mock_query.first.return_value = existing
            return mock_query

        mock_session.query.return_value.filter.side_effect = mock_filter

        response = test_client.post(
            "/api/v1/ai-systems/import",
            files={"file": ("test.csv", BytesIO(csv_content), "text/csv")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 1
        assert len(data["errors"]) == 1
        assert "duplicate" in data["errors"][0]["error"].lower()

    def test_non_csv_file_returns_400(self, client):
        """Non-CSV file returns 400 status code."""
        test_client, mock_session = client

        response = test_client.post(
            "/api/v1/ai-systems/import",
            files={"file": ("test.txt", BytesIO(b"not a csv file content"), "text/plain")}
        )

        assert response.status_code == 400
        assert "Invalid CSV" in response.json()["detail"]

    def test_empty_csv_returns_zero_created(self, client):
        """Empty CSV returns 0 created with no errors."""
        test_client, mock_session = client

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
        test_client, mock_session = client

        csv_content = textwrap.dedent("""\
            name,description,use_case,sector,version
            ,Missing name 1,Test,Test,1.0
            Duplicate Test,First occurrence,Test,Test,1.0
            Duplicate Test,Second occurrence,Test,Test,1.0
        """).strip().encode("utf-8")

        call_count = [0]
        def mock_filter(*args, **kwargs):
            mock_query = MagicMock()
            call_count[0] += 1
            if call_count[0] == 3:
                mock_query.first.return_value = MagicMock()
            else:
                mock_query.first.return_value = None
            return mock_query

        mock_session.query.return_value.filter.side_effect = mock_filter

        response = test_client.post(
            "/api/v1/ai-systems/import",
            files={"file": ("test.csv", BytesIO(csv_content), "text/csv")}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["created"] == 1
        assert len(data["errors"]) == 2

    def test_response_has_correct_schema(self, client):
        """Response has correct BulkImportResponse schema."""
        test_client, mock_session = client

        csv_content = textwrap.dedent("""\
            name,description,use_case,sector,version
            Test System,Test description,Test,Test,1.0
        """).strip().encode("utf-8")

        mock_session.query.return_value.filter.return_value.first.return_value = None

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