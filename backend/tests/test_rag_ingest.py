"""
Tests for POST /api/v1/rag/ingest — multipart PDF upload & FAISS index merge.

Follows the same mock-heavy, no-external-dep pattern used across this test suite.
All heavy dependencies (embeddings, FAISS, PyPDFLoader) are patched so the tests
run without an OpenAI key, a running DB, or any real PDFs on disk.
"""

import io
import pytest
from unittest.mock import MagicMock, patch
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

# Patch the two RAG functions called inside the endpoint
PATCH_LOAD_DOCS = "app.api.v1.rag.load_documents_from_paths"
PATCH_MERGE_VS = "app.api.v1.rag.merge_into_vector_store"

# Patch os.path helpers *inside the rag module* so we don't break
# tempfile / shutil operations that also rely on the real os.path.
PATCH_OS_EXISTS = "app.api.v1.rag.os.path.exists"
PATCH_OS_GETSIZE = "app.api.v1.rag.os.path.getsize"

# Patch the SHA-256 helper so tests don't need real file I/O
PATCH_SHA256 = "app.api.v1.rag._sha256_file"


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

    @patch(PATCH_SHA256, return_value="a" * 64)
    @patch(PATCH_MERGE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_single_pdf_success(self, mock_load, mock_merge, mock_hash, client, mock_rag_user):
        """
        1. Uploading a single valid PDF should return 200 with correct fields.
        """
        # Arrange: loader returns 5 fake chunks, FAISS index files exist
        mock_chunks = [MagicMock() for _ in range(5)]
        for c in mock_chunks:
            c.metadata = {"source": "eu_ai_act.pdf"}
        mock_load.return_value = mock_chunks
        mock_merge.return_value = (MagicMock(), mock_chunks)

        with (
            patch(PATCH_OS_EXISTS, return_value=True),
            patch(PATCH_OS_GETSIZE, return_value=512_000),
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

    @patch(PATCH_SHA256, return_value="b" * 64)
    @patch(PATCH_MERGE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_multiple_pdfs_success(self, mock_load, mock_merge, mock_hash, client, mock_rag_user):
        """
        2. Uploading multiple PDFs should reflect all files in the response.
        """
        mock_chunks = [MagicMock() for _ in range(42)]
        for c in mock_chunks:
            c.metadata = {"source": "doc.pdf"}
        mock_load.return_value = mock_chunks
        mock_merge.return_value = (MagicMock(), mock_chunks)

        with (
            patch(PATCH_OS_EXISTS, return_value=True),
            patch(PATCH_OS_GETSIZE, return_value=100_000),
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

    @patch(PATCH_MERGE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_non_pdf_file_returns_400(self, mock_load, mock_merge, client, mock_rag_user):
        """
        4. Uploading a non-PDF file should return 400 with a clear message.
        """
        response = client.post(
            "/api/v1/rag/ingest",
            files={"files": ("report.docx", io.BytesIO(b"fake docx"), "application/vnd.openxmlformats-officedocument")},
        )

        assert response.status_code == 400
        assert "pdf" in response.json()["detail"].lower()
        # Loader and FAISS builder must NOT have been called
        mock_load.assert_not_called()
        mock_merge.assert_not_called()

    @patch(PATCH_MERGE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_empty_pdf_returns_400(self, mock_load, mock_merge, client, mock_rag_user):
        """
        5. A valid-looking PDF that produces zero chunks should return 400.
        This covers scanned/image-only PDFs and password-protected files.
        """
        mock_load.return_value = []   # loader returns nothing
        mock_merge.return_value = (MagicMock(), [])

        response = client.post(
            "/api/v1/rag/ingest",
            files={"files": _make_pdf_upload("blank.pdf")},
        )

        assert response.status_code == 400
        assert "text" in response.json()["detail"].lower()
        mock_merge.assert_not_called()

    # ------------------------------------------------------------------
    # Downstream failures
    # ------------------------------------------------------------------

    @patch(PATCH_MERGE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_faiss_build_failure_returns_503(self, mock_load, mock_merge, client, mock_rag_user):
        """
        6. If the FAISS merge step raises an exception, the endpoint should
        return 503 with the error forwarded in the detail field.
        """
        mock_load.return_value = [MagicMock()]
        mock_merge.side_effect = RuntimeError("Embedding model unavailable")

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
        """
        # Make sure no auth override is active
        app.dependency_overrides.pop(get_current_user, None)

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
            app.dependency_overrides.pop(get_current_user, None)

    # ------------------------------------------------------------------
    # Response schema
    # ------------------------------------------------------------------

    @patch(PATCH_SHA256, return_value="c" * 64)
    @patch(PATCH_MERGE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_response_has_all_required_fields(self, mock_load, mock_merge, mock_hash, client, mock_rag_user):
        """
        8. The JSON response must contain exactly the three fields required
        by the issue specification.
        """
        mock_chunks = [MagicMock() for _ in range(10)]
        for c in mock_chunks:
            c.metadata = {"source": "test.pdf"}
        mock_load.return_value = mock_chunks
        mock_merge.return_value = (MagicMock(), mock_chunks)

        with (
            patch(PATCH_OS_EXISTS, return_value=True),
            patch(PATCH_OS_GETSIZE, return_value=1024),
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
    # Metadata persistence (IngestedDocument)
    # ------------------------------------------------------------------

    @patch(PATCH_SHA256, return_value="d" * 64)
    @patch(PATCH_MERGE_VS)
    @patch(PATCH_LOAD_DOCS)
    def test_ingest_creates_document_record(self, mock_load, mock_merge, mock_hash, client, mock_rag_user, db_session):
        """
        9. A successful ingestion should create an IngestedDocument row
        in the database with the correct metadata.
        """
        from app.models.ingested_document import IngestedDocument

        mock_chunks = [MagicMock() for _ in range(7)]
        for c in mock_chunks:
            c.metadata = {"source": "compliance_policy.pdf"}
        mock_load.return_value = mock_chunks
        mock_merge.return_value = (MagicMock(), mock_chunks)

        with (
            patch(PATCH_OS_EXISTS, return_value=True),
            patch(PATCH_OS_GETSIZE, return_value=2048),
        ):
            response = client.post(
                "/api/v1/rag/ingest",
                files={"files": _make_pdf_upload("compliance_policy.pdf")},
            )

        assert response.status_code == 200

        # Verify the DB row was created
        records = db_session.query(IngestedDocument).all()
        assert len(records) >= 1
        latest = records[-1]
        assert latest.filename == "compliance_policy.pdf"
        assert latest.file_hash == "d" * 64
        assert latest.chunk_count == 7
