import sys
import types
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models.user import User, SubscriptionTier


class DummyDoc:
    def __init__(self, source, page_content=""):
        self.metadata = {"source": source}
        self.page_content = page_content


def _get_test_db_session():
    """Creates a fresh in-memory database and returns a sessionmaker."""
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    return TestingSessionLocal


@pytest.fixture
def client():
    # 1. Setup fresh in-memory DB
    SessionLocal = _get_test_db_session()
    db = SessionLocal()

    # 2. Seed a test user so foreign keys in RagQuery work
    user = User(
        id=1,
        email="tester@example.com",
        hashed_password="fakehash",
        subscription_tier=SubscriptionTier.FREE,
        is_active=True
    )
    db.add(user)
    
    # Add an admin user as well
    admin = User(
        id=2,
        email="admin@example.com",
        hashed_password="fakehash",
        subscription_tier=SubscriptionTier.SCALE,
        is_active=True
    )
    db.add(admin)
    db.commit()

    # 3. Define dependency overrides
    def _override_get_db():
        try:
            yield db
        finally:
            pass # Keep it open for the duration of the test

    def _fake_user():
        return user

    app.dependency_overrides[get_db] = _override_get_db
    app.dependency_overrides[get_current_user] = _fake_user

    with TestClient(app) as c:
        yield c
    
    # 4. Cleanup
    db.close()
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
        "source_documents": [
            DummyDoc("doc1.pdf#chunk1", "According to Article 10 paragraph 2, testing is required."),
            DummyDoc("doc2.pdf#chunk2", "See Article 14 paragraph 1 for human oversight."),
        ],
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
    assert "sources" in data
    assert isinstance(data["sources"], list)
    assert len(data["sources"]) == 2

    first = data["sources"][0]
    assert first["filename"] == "doc1.pdf"
    assert first["article"] == "Article 10"
    assert first["paragraph"] == 2
    assert "answer" in data and data["answer"] == "Test answer"
    assert "answer_id" in data
    answer_id = data["answer_id"]

    # 2. Submit a thumbs-down feedback entry for that answer
    resp2 = client.post("/api/v1/rag/feedback", json={"answer_id": answer_id, "vote": "down"})
    assert resp2.status_code == 200

    # 3. Route authentication override to test admin extraction privileges
    def _admin_user():
        u = User(id=2, subscription_tier=SubscriptionTier.SCALE)
        return u

    app.dependency_overrides[get_current_user] = _admin_user

    # 4. Verify chunk tracking extraction logic works seamlessly
    resp3 = client.get("/api/v1/rag/low-quality-chunks?threshold=0.0")
    assert resp3.status_code == 200
    out = resp3.json()
    assert "low_quality_chunks" in out
    
    chunks = {c["chunk"] for c in out["low_quality_chunks"]}
    assert "doc1.pdf#chunk1" in chunks or "doc2.pdf#chunk2" in chunks


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
        u = User(id=2, subscription_tier=SubscriptionTier.SCALE)
        return u

    app.dependency_overrides[get_current_user] = _admin_user

    resp3 = client.get("/api/v1/rag/low-quality-chunks?threshold=0.0")
    assert resp3.status_code == 200
    assert resp3.json()["low_quality_chunks"] == []