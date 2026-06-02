import sys
import types
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models.user import User, SubscriptionTier


class DummyDoc:
    """Lightweight document mock for RAG tests."""
    def __init__(self, page_content):
        self.page_content = page_content
        self.metadata = {"source": page_content}


def _get_test_db():
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    return _override_get_db


@pytest.fixture
def client():
    # Setup fresh DB and auth overrides
    app.dependency_overrides[get_db] = _get_test_db()

    def _fake_user():
        u = User()
        u.id = 1
        u.email = "tester@example.com"
        u.subscription_tier = SubscriptionTier.FREE
        return u

    app.dependency_overrides[get_current_user] = _fake_user

    with TestClient(app) as c:
        yield c
    
    # Clean up overrides after test to prevent leakage
    app.dependency_overrides.clear()


@pytest.fixture
def mock_rag_modules():
    """Mocks RAG modules to avoid heavy dependencies and external API calls."""
    retrieval_chain_mod = types.ModuleType("app.modules.rag.retrieval_chain")
    groundedness_mod = types.ModuleType("app.modules.rag.groundedness")
    ml_flow_mod = types.ModuleType("app.modules.rag.ml_flow")

    # We'll override the qa_chain result in individual tests if needed
    fake_result = {
        "result": "Test answer", 
        "source_documents": [DummyDoc("doc1.pdf#chunk1"), DummyDoc("doc2.pdf#chunk2")]
    }
    
    retrieval_chain_mod.get_qa_chain = lambda: lambda payload: fake_result
    groundedness_mod.compute_groundedness = lambda answer, chunks: 0.85
    ml_flow_mod.log_query = lambda **kwargs: None

    with patch.dict(
        sys.modules,
        {
            "app.modules.rag.retrieval_chain": retrieval_chain_mod,
            "app.modules.rag.groundedness": groundedness_mod,
            "app.modules.rag.ml_flow": ml_flow_mod,
        },
    ):
        yield retrieval_chain_mod, groundedness_mod


def test_query_feedback_and_low_quality_flow(client, mock_rag_modules):
    """Tests the query, feedback, and admin low-quality chunk extraction pipeline."""
    # 1. Execute the standard query flow
    resp = client.post("/api/v1/rag/query", json={"question": "What is X?"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["answer"] == "Test answer"
    assert "answer_id" in data
    answer_id = data["answer_id"]

    # 2. Submit a thumbs-down feedback entry for that answer
    resp2 = client.post("/api/v1/rag/feedback", json={"answer_id": answer_id, "vote": "down"})
    assert resp2.status_code == 200

    # 3. Route authentication override to test admin extraction privileges
    def _admin_user():
        u = User()
        u.id = 2
        u.email = "admin@example.com"
        u.subscription_tier = SubscriptionTier.SCALE
        return u

    app.dependency_overrides[get_current_user] = _admin_user

    # 4. Verify chunk tracking extraction logic works seamlessly
    resp3 = client.get("/api/v1/rag/low-quality-chunks?threshold=0.0")
    assert resp3.status_code == 200
    out = resp3.json()
    assert "low_quality_chunks" in out
    
    chunks = {c["chunk"] for c in out["low_quality_chunks"]}
    assert "doc1.pdf#chunk1" in chunks or "doc2.pdf#chunk2" in chunks


def test_rag_query_length_validation(client):
    """Verify that queries longer than 2000 characters or empty are rejected with HTTP 422."""
    # Long question
    long_question = "x" * 2001
    resp = client.post("/api/v1/rag/query", json={"question": long_question})
    assert resp.status_code == 422

    # Empty question
    empty_question = ""
    resp = client.post("/api/v1/rag/query", json={"question": empty_question})
    assert resp.status_code == 422


def test_feedback_rejects_invalid_vote_value(client, mock_rag_modules):
    """Ensure that feedback only accepts valid vote values ('up', 'down')."""
    # 1. Get an answer ID
    resp = client.post("/api/v1/rag/query", json={"question": "What is X?"})
    assert resp.status_code == 200
    answer_id = resp.json()["answer_id"]

    # 2. Submit invalid vote
    resp2 = client.post(
        "/api/v1/rag/feedback",
        json={"answer_id": answer_id, "vote": "maybe"},
    )
    assert resp2.status_code == 422

    # 3. Verify admin extraction remains empty
    def _admin_user():
        u = User()
        u.id = 2
        u.email = "admin@example.com"
        u.subscription_tier = SubscriptionTier.SCALE
        return u

    app.dependency_overrides[get_current_user] = _admin_user

    resp3 = client.get("/api/v1/rag/low-quality-chunks?threshold=0.0")
    assert resp3.status_code == 200
    assert resp3.json()["low_quality_chunks"] == []
