"""
Tests for POST /api/v1/rag/ingest — multipart PDF upload & FAISS index rebuild.

Follows the same mock-heavy, no-external-dep pattern used across this test suite.
All heavy dependencies (embeddings, FAISS, PyPDFLoader) are patched so the tests
run without an OpenAI key, a running DB, or any real PDFs on disk.
"""

import io
import pytest
from unittest.mock import MagicMock, patch
from pypdf.errors import PdfReadError
from app.core.security import get_current_user
from app.main import app

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

# Patch get_current_user so we never need a real JWT
PATCH_AUTH = "app.core.security.get_current_user"

# Patch the two RAG functions called inside the endpoint
PATCH_LOAD_DOCS = "app.api.v1.rag.load_documents_from_paths"
PATCH_CREATE_VS = "app.api.v1.rag.create_vector_store"


@pytest.fixture
def mock_rag_user():
    """Authenticate RAG ingest tests without requiring a real JWT."""
    app.dependency_overrides[get_current_user] = _mock_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


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
    def test_single_pdf_success(self, mock_load, mock_create, client, mock_rag_user):
        """
        1. Uploading a single valid PDF should return 200 with correct fields.
        """
        # Arrange: loader returns 5 fake chunks, FAISS index files exist
        mock_chunks = [MagicMock() for _ in range(5)]
        mock_load.return_value = mock_chunks
        mock_create.return_value = MagicMock()

        with (
            patch(PATCH_AUTH, return_value=_mock_current_user()),
            patch("os.path.exists", return_value=True),
            patch("os.path.getsize", return_value=512_000),
        ):
            response = client.post(
                "/api/v1/rag/ingest",
                files={"files": _make_pdf_upload("eu_ai_act.pdf")},
            )

        # Assert
        assert response.status_code == 200
        data = response.json()
        assert data["files_processed"] == 1
        assert data["chunks_created"] == 5
        # two files × 512_000 bytes each
        assert data["index_size_bytes"] == 1_024_000

    @patch(PATCH_CREATE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_multiple_pdfs_success(self, mock_load, mock_create, client, mock_rag_user):
        """
        2. Uploading multiple PDFs should reflect all files in the response.
        """
        mock_chunks = [MagicMock() for _ in range(42)]
        mock_load.return_value = mock_chunks
        mock_create.return_value = MagicMock()

        with (
            patch(PATCH_AUTH, return_value=_mock_current_user()),
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

    def test_no_files_returns_422(self, client, mock_rag_user):
        """
        3. Sending an empty request (no 'files' field) should return 422.
        FastAPI validates the required File(...) parameter before our code runs.
        """
        response = client.post("/api/v1/rag/ingest")

        assert response.status_code == 422

    @patch(PATCH_CREATE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_non_pdf_file_returns_400(self, mock_load, mock_create, client, mock_rag_user):
        """
        4. Uploading a non-PDF file should return 400 with a clear message.
        """
        with patch(PATCH_AUTH, return_value=_mock_current_user()):
            response = client.post(
                "/api/v1/rag/ingest",
                files={"files": ("report.docx", io.BytesIO(b"fake docx"), "application/vnd.openxmlformats-officedocument")},
            )

        assert response.status_code == 400
        assert "pdf" in response.json()["detail"].lower()
        # Loader and FAISS builder must NOT have been called
        mock_load.assert_not_called()
        mock_create.assert_not_called()

    @patch(PATCH_CREATE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_empty_pdf_returns_400(self, mock_load, mock_create, client, mock_rag_user):
        """
        5. A valid-looking PDF that produces zero chunks should return 400.
        This covers scanned/image-only PDFs and password-protected files.
        """
        mock_load.return_value = []   # loader returns nothing
        mock_create.return_value = MagicMock()

        with patch(PATCH_AUTH, return_value=_mock_current_user()):
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
    def test_faiss_build_failure_returns_503(self, mock_load, mock_create, client, mock_rag_user):
        """
        6. If the FAISS build step raises an exception, the endpoint should
        return 503 with the error forwarded in the detail field.
        """
        mock_load.return_value = [MagicMock()]
        mock_create.side_effect = RuntimeError("Embedding model unavailable")

        with patch(PATCH_AUTH, return_value=_mock_current_user()):
            response = client.post(
                "/api/v1/rag/ingest",
                files={"files": _make_pdf_upload("eu_ai_act.pdf")},
            )

        assert response.status_code == 503
        assert "FAISS" in response.json()["detail"]
        assert "Embedding model unavailable" in response.json()["detail"]

    @patch(PATCH_CREATE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_pdf_parser_failure_returns_400(self, mock_load, mock_create, client, mock_rag_user):
        """Malformed or encrypted PDFs should return a sanitized client error."""
        mock_load.side_effect = PdfReadError("sensitive parser detail")

        with patch(PATCH_AUTH, return_value=_mock_current_user()):
            response = client.post(
                "/api/v1/rag/ingest",
                files={"files": _make_pdf_upload("broken.pdf")},
            )

        assert response.status_code == 400
        assert "sensitive parser detail" not in response.json()["detail"]
        mock_create.assert_not_called()

    @patch(PATCH_CREATE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_unexpected_loader_failure_returns_503(self, mock_load, mock_create, client, mock_rag_user):
        """Unexpected loader failures should be logged without leaking details."""
        mock_load.side_effect = RuntimeError("sensitive storage detail")

        with patch(PATCH_AUTH, return_value=_mock_current_user()):
            response = client.post(
                "/api/v1/rag/ingest",
                files={"files": _make_pdf_upload("valid.pdf")},
            )

        assert response.status_code == 503
        assert "sensitive storage detail" not in response.json()["detail"]
        mock_create.assert_not_called()

    # ------------------------------------------------------------------
    # Auth
    # ------------------------------------------------------------------

    def test_unauthenticated_request_returns_401(self, client):
        """
        7. A request without a valid JWT should be rejected before the
        endpoint logic runs at all.
        """
        # Override the conftest's default auth to force an actual 401
        from app.core.security import get_current_user
        from fastapi import HTTPException, status
        
        def raise_unauthorized():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )
        
        app.dependency_overrides[get_current_user] = raise_unauthorized
        
        try:
            response = client.post(
                "/api/v1/rag/ingest",
                files={"files": _make_pdf_upload()},
            )
            # FastAPI returns 401 or 403 depending on the security scheme
            assert response.status_code in (401, 403)
        finally:
            # Remove the override so the conftest fixture can clean up cleanly
            app.dependency_overrides.pop(get_current_user, None)

    # ------------------------------------------------------------------
    # Response schema
    # ------------------------------------------------------------------

    @patch(PATCH_CREATE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_response_has_all_required_fields(self, mock_load, mock_create, client, mock_rag_user):
        """
        8. The JSON response must contain exactly the three fields required
        by the issue specification.
        """
        mock_load.return_value = [MagicMock() for _ in range(10)]
        mock_create.return_value = MagicMock()

        with (
            patch(PATCH_AUTH, return_value=_mock_current_user()),
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
        # All values should be non-negative integers
        assert isinstance(data["files_processed"], int) and data["files_processed"] >= 0
        assert isinstance(data["chunks_created"], int) and data["chunks_created"] >= 0
        assert isinstance(data["index_size_bytes"], int) and data["index_size_bytes"] >= 0

    # ------------------------------------------------------------------
    # Rate and size limit checks
    # ------------------------------------------------------------------

    def test_too_many_files_returns_413(self, client, mock_rag_user):
        """
        9. Uploading more files than RAG_MAX_FILES_PER_REQUEST should return 413.
        """
        from app.core.config import settings
        with (
            patch(PATCH_AUTH, return_value=_mock_current_user()),
            patch.object(settings, "RAG_MAX_FILES_PER_REQUEST", 2)
        ):
            response = client.post(
                "/api/v1/rag/ingest",
                files=[
                    ("files", _make_pdf_upload("doc1.pdf")),
                    ("files", _make_pdf_upload("doc2.pdf")),
                    ("files", _make_pdf_upload("doc3.pdf")),
                ],
            )
        assert response.status_code == 413
        assert "too many files" in response.json()["detail"].lower()

    def test_oversized_file_returns_413(self, client, mock_rag_user):
        """
        10. Uploading a file exceeding RAG_MAX_FILE_SIZE_BYTES should return 413.
        """
        from app.core.config import settings
        with (
            patch(PATCH_AUTH, return_value=_mock_current_user()),
            patch.object(settings, "RAG_MAX_FILE_SIZE_BYTES", 10)
        ):
            response = client.post(
                "/api/v1/rag/ingest",
                files={"files": _make_pdf_upload("large.pdf", content=b"A" * 11)},
            )
        assert response.status_code == 413
        assert "exceeds the maximum size" in response.json()["detail"].lower()

    def test_exceed_total_budget_returns_413(self, client, mock_rag_user):
        """
        11. Uploading multiple files exceeding RAG_TOTAL_BUDGET_BYTES should return 413.
        """
        from app.core.config import settings
        with (
            patch(PATCH_AUTH, return_value=_mock_current_user()),
            patch.object(settings, "RAG_TOTAL_BUDGET_BYTES", 20)
        ):
            response = client.post(
                "/api/v1/rag/ingest",
                files=[
                    ("files", _make_pdf_upload("doc1.pdf", content=b"A" * 15)),
                    ("files", _make_pdf_upload("doc2.pdf", content=b"A" * 15)),
                ],
            )
        assert response.status_code == 413
        assert "total upload size exceeds" in response.json()["detail"].lower()
