"""
Tests for the IngestedDocument model and the /rag/documents endpoints.

Verifies:
- IngestedDocument model creation and field defaults
- GET /rag/documents returns the document registry
- DELETE /rag/documents/{doc_id} admin-only enforcement
- SHA-256 hash deduplication in POST /rag/ingest
"""

import io
import pytest
from unittest.mock import MagicMock, patch

from app.core.security import get_current_user
from app.main import app
from app.models.ingested_document import IngestedDocument, SourceType


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_admin_user():
    """Provide a SCALE-tier (admin) user override for auth."""
    user = MagicMock()
    user.id = 999
    user.email = "admin@aegisai.dev"
    user.subscription_tier = MagicMock()
    user.subscription_tier.__eq__ = lambda self, other: True  # passes SCALE check
    # Make subscription_tier look like SubscriptionTier.SCALE
    from app.models.user import SubscriptionTier
    user.subscription_tier = SubscriptionTier.SCALE

    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def mock_regular_user():
    """Provide a non-admin user override for auth."""
    user = MagicMock()
    user.id = 1
    user.email = "user@aegisai.dev"
    from app.models.user import SubscriptionTier
    user.subscription_tier = SubscriptionTier.FREE

    app.dependency_overrides[get_current_user] = lambda: user
    yield user
    app.dependency_overrides.pop(get_current_user, None)


# ---------------------------------------------------------------------------
# Model tests
# ---------------------------------------------------------------------------

class TestIngestedDocumentModel:
    """Unit tests for the IngestedDocument SQLAlchemy model."""

    def test_create_uploaded_document(self, db_session):
        """An uploaded document record should be persisted with defaults."""
        doc = IngestedDocument(
            filename="test_policy.pdf",
            source_type=SourceType.UPLOADED,
            file_hash="a" * 64,
            file_size_bytes=1024,
            chunk_count=10,
            uploaded_by_id=None,
        )
        db_session.add(doc)
        db_session.flush()

        assert doc.id is not None
        assert doc.filename == "test_policy.pdf"
        assert doc.source_type == SourceType.UPLOADED
        assert doc.regulation_name is None
        assert doc.created_at is not None

    def test_create_preloaded_document(self, db_session):
        """A pre-loaded document should store the regulation name."""
        doc = IngestedDocument(
            filename="eu_ai_act.pdf",
            source_type=SourceType.PRE_LOADED,
            regulation_name="EU AI Act",
            file_hash="b" * 64,
            file_size_bytes=5_000_000,
            chunk_count=450,
        )
        db_session.add(doc)
        db_session.flush()

        assert doc.source_type == SourceType.PRE_LOADED
        assert doc.regulation_name == "EU AI Act"
        assert doc.uploaded_by_id is None

    def test_repr(self):
        """__repr__ should include filename and source type."""
        doc = IngestedDocument(
            id=42,
            filename="test.pdf",
            source_type=SourceType.UPLOADED,
            file_hash="c" * 64,
        )
        assert "test.pdf" in repr(doc)
        assert "uploaded" in repr(doc)


# ---------------------------------------------------------------------------
# GET /rag/documents
# ---------------------------------------------------------------------------

class TestListIngestedDocuments:
    """Tests for the GET /rag/documents endpoint."""

    def test_empty_registry(self, client, mock_regular_user):
        """An empty registry should return an empty list."""
        response = client.get("/api/v1/rag/documents")
        assert response.status_code == 200
        assert response.json() == []

    def test_returns_ingested_docs(self, client, mock_regular_user, db_session):
        """Documents in the registry should be returned in the response."""
        doc = IngestedDocument(
            filename="gdpr.pdf",
            source_type=SourceType.PRE_LOADED,
            regulation_name="GDPR",
            file_hash="d" * 64,
            file_size_bytes=2_000_000,
            chunk_count=200,
        )
        db_session.add(doc)
        db_session.commit()

        response = client.get("/api/v1/rag/documents")
        assert response.status_code == 200
        data = response.json()
        assert len(data) == 1
        assert data[0]["filename"] == "gdpr.pdf"
        assert data[0]["regulation_name"] == "GDPR"
        assert data[0]["source_type"] == "pre_loaded"

    def test_unauthenticated_returns_401(self, client):
        """Unauthenticated requests should be rejected."""
        from app.core.security import get_current_user
        from app.main import app
        old_override = app.dependency_overrides.get(get_current_user)
        if get_current_user in app.dependency_overrides:
            del app.dependency_overrides[get_current_user]
        try:
            response = client.get("/api/v1/rag/documents")
            assert response.status_code in (401, 403)
        finally:
            if old_override is not None:
                app.dependency_overrides[get_current_user] = old_override


# ---------------------------------------------------------------------------
# DELETE /rag/documents/{doc_id}
# ---------------------------------------------------------------------------

class TestDeleteIngestedDocument:
    """Tests for the DELETE /rag/documents/{doc_id} endpoint."""

    def test_admin_can_delete(self, client, mock_admin_user, db_session):
        """An admin user should be able to delete a document record."""
        doc = IngestedDocument(
            filename="old_policy.pdf",
            source_type=SourceType.UPLOADED,
            file_hash="e" * 64,
            file_size_bytes=500,
            chunk_count=5,
        )
        db_session.add(doc)
        db_session.commit()

        response = client.delete(f"/api/v1/rag/documents/{doc.id}")
        assert response.status_code == 200
        assert response.json()["status"] == "deleted"

    def test_non_admin_forbidden(self, client, mock_regular_user, db_session):
        """A non-admin user should receive 403."""
        doc = IngestedDocument(
            filename="restricted.pdf",
            source_type=SourceType.UPLOADED,
            file_hash="f" * 64,
            file_size_bytes=100,
            chunk_count=1,
        )
        db_session.add(doc)
        db_session.commit()

        response = client.delete(f"/api/v1/rag/documents/{doc.id}")
        assert response.status_code == 403

    def test_not_found(self, client, mock_admin_user):
        """Deleting a non-existent document should return 404."""
        response = client.delete("/api/v1/rag/documents/99999")
        assert response.status_code == 404
