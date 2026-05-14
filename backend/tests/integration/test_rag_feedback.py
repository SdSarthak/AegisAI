import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import importlib
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models.user import User, SubscriptionTier


class DummyDoc:
    def __init__(self, source):
        self.metadata = {"source": source}


def _get_test_db():
    engine = create_engine("sqlite:///:memory:")
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
    app.dependency_overrides[get_db] = _get_test_db()

    # override auth to return a user; default non-admin
    def _fake_user():
        u = User()
        u.id = 1
        u.email = "tester@example.com"
        u.subscription_tier = SubscriptionTier.FREE
        return u

    app.dependency_overrides[get_current_user] = _fake_user

    with TestClient(app) as c:
        yield c


def test_query_feedback_and_low_quality_flow(client):
    # Mock the QA chain to return controlled result and sources
    fake_result = {"result": "Test answer", "source_documents": [DummyDoc("doc1.pdf#chunk1"), DummyDoc("doc2.pdf#chunk2")]}

    # Provide a lightweight fake retrieval_chain module (avoid heavy langchain imports)
    import types, sys

    mod = types.ModuleType("app.modules.rag.retrieval_chain")

    def _fake_get_qa_chain():
        return lambda payload: fake_result

    mod.get_qa_chain = _fake_get_qa_chain
    sys.modules["app.modules.rag.retrieval_chain"] = mod

    # Call query endpoint
    resp = client.post("/api/v1/rag/query", json={"question": "What is X?"})
    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data and data["answer"] == "Test answer"
    assert "answer_id" in data
    answer_id = data["answer_id"]

    # Submit a thumbs-down for that answer
    resp2 = client.post("/api/v1/rag/feedback", json={"answer_id": answer_id, "vote": "down"})
    assert resp2.status_code == 200

    # Now query low-quality-chunks as admin: override current_user to be admin
    def _admin_user():
        u = User()
        u.id = 2
        u.email = "admin@example.com"
        u.subscription_tier = SubscriptionTier.SCALE
        return u

    app.dependency_overrides[get_current_user] = _admin_user

    resp3 = client.get("/api/v1/rag/low-quality-chunks?threshold=0.0")
    assert resp3.status_code == 200
    out = resp3.json()
    assert "low_quality_chunks" in out
    # Should contain our two chunks (since total feedback for the answer was 1 down)
    chunks = {c["chunk"] for c in out["low_quality_chunks"]}
    assert "doc1.pdf#chunk1" in chunks or "doc2.pdf#chunk2" in chunks
