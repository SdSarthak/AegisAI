"""Regression tests for POST /api/v1/rag/query.

Verifies that the endpoint does not crash with a NameError when using
``time.monotonic()`` (the ``time`` module must be imported at the top of
``backend/app/api/v1/rag.py``).
"""

import sys
import types
from unittest.mock import MagicMock, patch

import pytest

from app.core.security import get_current_user
from app.models.user import SubscriptionTier
from app.main import app


class _DummyDoc:
    def __init__(self, source: str):
        self.page_content = source
        self.metadata = {"source": source}


def _mock_current_user():
    user = MagicMock()
    user.id = 1
    user.email = "test@example.com"
    user.full_name = "Test User"
    user.subscription_tier = SubscriptionTier.FREE
    user.is_active = True
    return user


@pytest.fixture
def mock_rag_user():
    """Authenticate as a mock user without requiring a real JWT."""
    app.dependency_overrides[get_current_user] = _mock_current_user
    yield
    app.dependency_overrides.pop(get_current_user, None)


@pytest.fixture
def mock_rag_modules():
    """Patch the lazily-imported RAG modules so the endpoint runs without
    external dependencies (OpenAI, FAISS, etc.)."""
    retrieval_chain = types.ModuleType("app.modules.rag.retrieval_chain")

    def _qa_chain(payload):
        return {
            "result": "Regulatory answer based on retrieved context.",
            "source_documents": [_DummyDoc("doc.pdf#chunk1")],
            "groundedness_score": 0.92,
            "low_confidence": False,
            "confidence_tier": "high",
            "per_verifier_scores": {},
            "flagged_reason": None,
        }

    retrieval_chain.get_qa_chain = lambda: _qa_chain
    ml_flow = types.ModuleType("app.modules.rag.ml_flow")
    ml_flow.log_query = lambda question, answer, sources, latency_ms: None

    with patch.dict(
        sys.modules,
        {
            "app.modules.rag.retrieval_chain": retrieval_chain,
            "app.modules.rag.ml_flow": ml_flow,
        },
    ):
        yield


class TestRagQuery:
    """Integration-style tests for the /rag/query endpoint."""

    def test_time_module_is_imported(self, mock_rag_modules):
        """Regression: the ``time`` module must be importable at the top of
        ``app.api.v1.rag``, otherwise ``time.monotonic()`` raises
        ``NameError: name 'time' is not defined`` at runtime."""
        import app.api.v1.rag as rag_module

        assert "time" in rag_module.__dict__, (
            "'time' must be imported at module level in rag.py "
            "to prevent NameError on time.monotonic()"
        )

    def test_query_returns_200_with_valid_answer(
        self, client, mock_rag_user, mock_rag_modules
    ):
        """The query endpoint should return 200 and include expected fields."""
        response = client.post(
            "/api/v1/rag/query",
            json={"question": "What are the requirements under Article 9?"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["answer"] == "Regulatory answer based on retrieved context."
        assert data["sources"] == ["doc.pdf#chunk1"]
        assert isinstance(data["groundedness_score"], (int, float))
        assert data["low_confidence"] is False

    def test_query_does_not_raise_nameerror(
        self, client, mock_rag_user, mock_rag_modules
    ):
        """Regression: calling the query endpoint must not trigger a NameError
        from ``time.monotonic()``."""
        response = client.post(
            "/api/v1/rag/query",
            json={"question": "Does the endpoint crash without the time import?"},
        )
        assert response.status_code == 200

    def test_unauthenticated_request_returns_401(
        self, client, mock_rag_modules
    ):
        """A request without a valid JWT should be rejected."""
        from fastapi import HTTPException, status

        def raise_unauthorized():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Not authenticated",
            )

        app.dependency_overrides[get_current_user] = raise_unauthorized
        try:
            response = client.post(
                "/api/v1/rag/query",
                json={"question": "Some question"},
            )
            assert response.status_code in (401, 403)
        finally:
            app.dependency_overrides.pop(get_current_user, None)
