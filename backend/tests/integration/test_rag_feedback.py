"""
Integration test: query → feedback → low-quality-chunks flow.
 
Uses an in-memory SQLite DB and patches all heavy external dependencies
(QA chain, MLflow) so no OpenAI key, FAISS index, or real PDFs are needed.
"""
 
import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient
 
from app.main import app
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User, SubscriptionTier
 
 
# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
 
class DummyDoc:
    """Minimal stand-in for a LangChain Document with a metadata source."""
    def __init__(self, source: str):
        self.metadata = {"source": source}
 
 
# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------
 
@pytest.fixture()
def rag_client(db_session):
    """
    TestClient that:
    - reuses the conftest StaticPool DB session (so all requests share
      the same in-memory SQLite connection and see each other's commits)
    - authenticates as a FREE-tier user by default
    - patches get_qa_chain and log_query so no FAISS / MLflow is needed
    """
 
    def _fake_user():
        u = User()
        u.id = 1
        u.email = "tester@example.com"
        u.subscription_tier = SubscriptionTier.FREE
        return u
 
    def _override_get_db():
        yield db_session
 
    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _fake_user
 
    fake_result = {
        "result": "Test answer",
        "source_documents": [
            DummyDoc("doc1.pdf#chunk1"),
            DummyDoc("doc2.pdf#chunk2"),
        ],
    }
 
    fake_chain = MagicMock(return_value=fake_result)
    fake_get_qa_chain = MagicMock(return_value=fake_chain)
 
    with (
        patch("app.api.v1.rag.get_qa_chain", fake_get_qa_chain),
        patch("app.api.v1.rag.log_query"),
    ):
        with TestClient(app) as c:
            yield c
 
    app.dependency_overrides.clear()
 
 
# ---------------------------------------------------------------------------
# Test
# ---------------------------------------------------------------------------
 
def test_query_feedback_and_low_quality_flow(rag_client):
    """
    End-to-end flow:
      1. POST /rag/query       → 200, answer returned
      2. POST /rag/feedback    → 200, thumbs-down recorded
      3. GET  /rag/low-quality-chunks (as admin) → 200, failing chunks listed
    """
 
    # ------------------------------------------------------------------
    # Step 1: query
    # ------------------------------------------------------------------
    resp = rag_client.post("/api/v1/rag/query", json={"question": "What is X?"})
    assert resp.status_code == 200, f"Query failed: {resp.text}"
 
    data = resp.json()
    assert data["answer"] == "Test answer"
    assert "answer_id" in data
    answer_id = data["answer_id"]
 
    # ------------------------------------------------------------------
    # Step 2: thumbs-down on that answer
    # ------------------------------------------------------------------
    resp2 = rag_client.post(
        "/api/v1/rag/feedback",
        json={"answer_id": answer_id, "vote": "down"},
    )
    assert resp2.status_code == 200, f"Feedback failed: {resp2.text}"
 
    # ------------------------------------------------------------------
    # Step 3: low-quality-chunks — must be requested as a SCALE-tier user
    # ------------------------------------------------------------------
    def _admin_user():
        u = User()
        u.id = 2
        u.email = "admin@example.com"
        u.subscription_tier = SubscriptionTier.SCALE
        return u
 
    app.dependency_overrides[get_current_user] = _admin_user
 
    resp3 = rag_client.get("/api/v1/rag/low-quality-chunks?threshold=0.0")
    assert resp3.status_code == 200, f"Low-quality-chunks failed: {resp3.text}"
 
    out = resp3.json()
    assert "low_quality_chunks" in out
 
    chunks = {c["chunk"] for c in out["low_quality_chunks"]}
    assert "doc1.pdf#chunk1" in chunks or "doc2.pdf#chunk2" in chunks, (
        f"Expected source chunks in low-quality list, got: {chunks}"
    )