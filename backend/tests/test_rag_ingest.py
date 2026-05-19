"""
Tests for POST /api/v1/rag/ingest — multipart PDF upload & FAISS index rebuild.

Follows the same mock-heavy, no-external-dep pattern used across this test suite.
All heavy dependencies (embeddings, FAISS, PyPDFLoader) are patched so the tests
run without an OpenAI key, a running DB, or any real PDFs on disk.
"""

import io
import pytest
from unittest.mock import MagicMock, patch
from fastapi import HTTPException, status
from fastapi.testclient import TestClient

from app.main import app
from app.core.security import get_current_user


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_pdf_upload(filename: str = "test.pdf", content: bytes = b"%PDF-1.4 fake"):
    """Return a tuple for use with TestClient multipart uploads."""
    return (filename, io.BytesIO(content), "application/pdf")


def _mock_current_user():
    """Return a minimal fake User object accepted by get_current_user."""
    user = MagicMock()
    user.id = "test-user-id"
    user.email = "test@example.com"
    return user


# ---------------------------------------------------------------------------
# Shared patches applied to every test in this module
# ---------------------------------------------------------------------------

# Patch the two RAG functions called inside the endpoint.
# These target the names as imported into the rag module, which is what
# FastAPI actually calls.
PATCH_LOAD_DOCS = "app.api.v1.rag.load_documents_from_paths"
PATCH_CREATE_VS = "app.api.v1.rag.create_vector_store"


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture(autouse=True)
def override_auth():
    """
    Install a dependency override for get_current_user on every test.

    Using app.dependency_overrides is the correct FastAPI mechanism — patching
    the module-level name with unittest.mock.patch does not affect what FastAPI
    calls because Depends() captures the function reference at import time.
    """
    app.dependency_overrides[get_current_user] = _mock_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture()
def client():
    """TestClient bound to the app with auth already overridden by override_auth."""
    with TestClient(app) as c:
        yield c


# ---------------------------------------------------------------------------
# Test class
# ---------------------------------------------------------------------------

class TestRagIngest:
    """Integration-style tests for the /rag/ingest endpoint."""

    # ------------------------------------------------------------------
    # Happy path
    # ------------------------------------------------------------------

    @patch(PATCH_CREATE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_single_pdf_success(self, mock_load, mock_create, client):
        """
        1. Uploading a single valid PDF should return 200 with correct fields.
        """
        mock_chunks = [MagicMock() for _ in range(5)]
        mock_load.return_value = mock_chunks
        mock_create.return_value = MagicMock()

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=512_000),
        ):
            response = client.post(
                "/api/v1/rag/ingest",
                files={"files": _make_pdf_upload("eu_ai_act.pdf")},
            )

        assert response.status_code == 200
        data = response.json()
        assert data["files_processed"] == 1
        assert data["chunks_created"] == 5
        # two index files × 512_000 bytes each
        assert data["index_size_bytes"] == 1_024_000

    @patch(PATCH_CREATE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_multiple_pdfs_success(self, mock_load, mock_create, client):
        """
        2. Uploading multiple PDFs should reflect all files in the response.
        """
        mock_chunks = [MagicMock() for _ in range(42)]
        mock_load.return_value = mock_chunks
        mock_create.return_value = MagicMock()

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=100_000),
        ):
            response = client.post(
                "/api/v1/rag/ingest",
                files=[
                    ("files", _make_pdf_upload("doc1.pdf")),
                    ("files", _make_pdf_upload("doc2.pdf")),
                    ("files", _make_pdf_upload("doc3.pdf")),
                ],
            )

        assert response.status_code == 200
        data = response.json()
        assert data["files_processed"] == 3
        assert data["chunks_created"] == 42

    # ------------------------------------------------------------------
    # Validation errors
    # ------------------------------------------------------------------

    def test_no_files_returns_422(self, client):
        """
        3. Sending an empty request (no 'files' field) should return 422.
        FastAPI validates the required File(...) parameter before our code runs.
        """
        response = client.post("/api/v1/rag/ingest")
        assert response.status_code == 422

    @patch(PATCH_CREATE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_non_pdf_file_returns_400(self, mock_load, mock_create, client):
        """
        4. Uploading a non-PDF file should return 400 with a clear message.
        """
        response = client.post(
            "/api/v1/rag/ingest",
            files={"files": (
                "report.docx",
                io.BytesIO(b"fake docx"),
                "application/vnd.openxmlformats-officedocument",
            )},
        )

        assert response.status_code == 400
        assert "pdf" in response.json()["detail"].lower()
        mock_load.assert_not_called()
        mock_create.assert_not_called()

    @patch(PATCH_CREATE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_empty_pdf_returns_400(self, mock_load, mock_create, client):
        """
        5. A valid-looking PDF that produces zero chunks should return 400.
        This covers scanned/image-only PDFs and password-protected files.
        """
        mock_load.return_value = []
        mock_create.return_value = MagicMock()

        response = client.post(
            "/api/v1/rag/ingest",
            files={"files": _make_pdf_upload("blank.pdf")},
        )

        assert response.status_code == 400
        assert "text" in response.json()["detail"].lower()
        mock_create.assert_not_called()

    # ------------------------------------------------------------------
    # Downstream failures
    # ------------------------------------------------------------------

    @patch(PATCH_CREATE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_faiss_build_failure_returns_503(self, mock_load, mock_create, client):
        """
        6. If the FAISS build step raises an exception the endpoint should
        return 503 with the error forwarded in the detail field.
        """
        mock_load.return_value = [MagicMock()]
        mock_create.side_effect = RuntimeError("Embedding model unavailable")

        response = client.post(
            "/api/v1/rag/ingest",
            files={"files": _make_pdf_upload("eu_ai_act.pdf")},
        )

        assert response.status_code == 503
        assert "FAISS" in response.json()["detail"]
        assert "Embedding model unavailable" in response.json()["detail"]

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def test_unauthenticated_request_returns_401(self, client):
        """
        7. A request without a valid JWT should be rejected before the
        endpoint logic runs at all.

        We temporarily replace the autouse override with one that raises 401,
        then restore the permissive override afterwards.
        """
        def raise_unauthorized():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )

        # Temporarily replace the autouse permissive override
        app.dependency_overrides[get_current_user] = raise_unauthorized
        try:
            response = client.post(
                "/api/v1/rag/ingest",
                files={"files": _make_pdf_upload()},
            )
            assert response.status_code in (401, 403)
        finally:
            # Restore the permissive override so the autouse fixture teardown
            # finds the key and cleans up cleanly
            app.dependency_overrides[get_current_user] = _mock_current_user

    # ------------------------------------------------------------------
    # Response schema
    # ------------------------------------------------------------------

    @patch(PATCH_CREATE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_response_has_all_required_fields(self, mock_load, mock_create, client):
        """
        8. The JSON response must contain exactly the three fields required
        by the issue specification.
        """
        mock_load.return_value = [MagicMock() for _ in range(10)]
        mock_create.return_value = MagicMock()

        with (
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=1024),
        ):
            response = client.post(
                "/api/v1/rag/ingest",
                files={"files": _make_pdf_upload()},
            )

        assert response.status_code == 200
        data = response.json()
        assert "files_processed" in data
        assert "chunks_created" in data
        assert "index_size_bytes" in data
        assert isinstance(data["files_processed"], int) and data["files_processed"] >= 0
        assert isinstance(data["chunks_created"], int) and data["chunks_created"] >= 0
        assert isinstance(data["index_size_bytes"], int) and data["index_size_bytes"] >= 0