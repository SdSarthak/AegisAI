import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
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
    """Tests the query, feedback, and admin low-quality chunk extraction pipeline."""
    import sys
    import types

    # 1. Define a clean, lightweight document mock inside the test block
    class DummyDoc:
        def __init__(self, page_content):
            self.page_content = page_content
            self.metadata = {"source": page_content}

    fake_result = {
        "result": "Test answer", 
        "source_documents": [DummyDoc("doc1.pdf#chunk1"), DummyDoc("doc2.pdf#chunk2")]
    }

    # 2. Build mock modules and inject them into sys.modules before the request.
    #    The endpoint lazily imports both ``retrieval_chain`` and ``groundedness``
    #    inside its ``try`` block.  ``patch.dict`` temporarily inserts them so that
    #    Python's import machinery finds the mocks instead of loading the real
    #    modules (which would fail due to missing external dependencies).
    retrieval_chain_mod = types.ModuleType("app.modules.rag.retrieval_chain")
    retrieval_chain_mod.get_qa_chain = lambda: lambda payload: fake_result

    groundedness_mod = types.ModuleType("app.modules.rag.groundedness")
    groundedness_mod.compute_groundedness = lambda answer, chunks: 0.85

    # 3. Execute the standard query flow with mocks in place
    with patch.dict(
        sys.modules,
        {
            "app.modules.rag.retrieval_chain": retrieval_chain_mod,
            "app.modules.rag.groundedness": groundedness_mod,
        },
    ):
        resp = client.post("/api/v1/rag/query", json={"question": "What is X?"})

    assert resp.status_code == 200
    data = resp.json()
    assert "answer" in data and data["answer"] == "Test answer"
    assert "answer_id" in data
    answer_id = data["answer_id"]

    # 4. Submit a thumbs-down feedback entry for that answer
    resp2 = client.post("/api/v1/rag/feedback", json={"answer_id": answer_id, "vote": "down"})
    assert resp2.status_code == 200

    # 5. Route authentication override to test admin extraction privileges
    def _admin_user():
        u = User()
        u.id = 2
        u.email = "admin@example.com"
        u.subscription_tier = SubscriptionTier.SCALE
        return u

    app.dependency_overrides[get_current_user] = _admin_user

    # 6. Verify chunk tracking extraction logic works seamlessly
    resp3 = client.get("/api/v1/rag/low-quality-chunks?threshold=0.0")
    assert resp3.status_code == 200
    out = resp3.json()
    assert "low_quality_chunks" in out

    chunks = {c["chunk"] for c in out["low_quality_chunks"]}
    assert "doc1.pdf#chunk1" in chunks or "doc2.pdf#chunk2" in chunks

    # 7. Clean up dependency overrides to prevent test leakage
    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]


@pytest.mark.parametrize("threshold", ["-0.1", "1.1"])
def test_low_quality_chunks_rejects_out_of_range_threshold(client, threshold):
    def _admin_user():
        u = User()
        u.id = 2
        u.email = "admin@example.com"
        u.subscription_tier = SubscriptionTier.SCALE
        return u

    app.dependency_overrides[get_current_user] = _admin_user

    response = client.get(f"/api/v1/rag/low-quality-chunks?threshold={threshold}")

    assert response.status_code == 422

    if get_current_user in app.dependency_overrides:
        del app.dependency_overrides[get_current_user]
