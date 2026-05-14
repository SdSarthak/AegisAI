import pytest
from fastapi.testclient import TestClient
from unittest.mock import patch
import importlib
from sqlalchemy import create_engine
from sqlalchemy import inspect
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.main import app
from app.core.database import Base, get_db
from app.core.security import get_current_user
from app.models.user import User, SubscriptionTier
from app.api.v1 import rag as rag_api


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
    fake_result = {
        "result": "Test answer",
        "source_documents": [DummyDoc("doc1.pdf#chunk1"), DummyDoc("doc2.pdf#chunk2")],
    }

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
    resp2 = client.post(
        "/api/v1/rag/feedback", json={"answer_id": answer_id, "vote": "down"}
    )
    assert resp2.status_code == 200

    # A different user should not be able to modify feedback
    def _other_user():
        u = User()
        u.id = 2
        u.email = "other@example.com"
        u.subscription_tier = SubscriptionTier.FREE
        return u

    app.dependency_overrides[get_current_user] = _other_user
    resp_denied = client.post(
        "/api/v1/rag/feedback", json={"answer_id": answer_id, "vote": "down"}
    )
    assert resp_denied.status_code == 404

    # Now query low-quality-chunks as admin: override current_user to be admin
    def _admin_user():
        u = User()
        u.id = 1
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

    # A different scale user should not see another tenant's feedback
    def _other_admin_user():
        u = User()
        u.id = 3
        u.email = "scale-other@example.com"
        u.subscription_tier = SubscriptionTier.SCALE
        return u

    app.dependency_overrides[get_current_user] = _other_admin_user
    resp4 = client.get("/api/v1/rag/low-quality-chunks?threshold=0.0")
    assert resp4.status_code == 200
    out_other = resp4.json()
    assert out_other["low_quality_chunks"] == []


def test_query_handles_legacy_rag_feedback_schema(client):
    engine = create_engine("sqlite:///:memory:")
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    with engine.begin() as conn:
        conn.execute(text("DROP TABLE rag_feedback"))
        conn.execute(
            text(
                """
                CREATE TABLE rag_feedback (
                    id VARCHAR(64) PRIMARY KEY,
                    question VARCHAR(2000),
                    answer VARCHAR(4000),
                    thumbs_up INTEGER,
                    thumbs_down INTEGER,
                    source_chunks JSON,
                    created_at DATETIME
                )
                """
            )
        )

    def _override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = _override_get_db

    def _fake_user():
        u = User()
        u.id = 1
        u.email = "tenant@example.com"
        u.subscription_tier = SubscriptionTier.FREE
        return u

    app.dependency_overrides[get_current_user] = _fake_user

    import types, sys

    mod = types.ModuleType("app.modules.rag.retrieval_chain")

    def _fake_get_qa_chain():
        return lambda payload: {
            "result": "Legacy schema answer",
            "source_documents": [DummyDoc("legacy.pdf#chunk1")],
        }

    mod.get_qa_chain = _fake_get_qa_chain
    sys.modules["app.modules.rag.retrieval_chain"] = mod

    resp = client.post("/api/v1/rag/query", json={"question": "Legacy table?"})
    assert resp.status_code == 200


def test_legacy_rag_feedback_table_gets_owner_column():
    engine = create_engine("sqlite:///:memory:")
    with engine.begin() as conn:
        conn.execute(
            text(
                """
                CREATE TABLE rag_feedback (
                    id VARCHAR(64) PRIMARY KEY,
                    question VARCHAR(2000),
                    answer VARCHAR(4000),
                    thumbs_up INTEGER,
                    thumbs_down INTEGER,
                    source_chunks JSON,
                    created_at DATETIME
                )
                """
            )
        )

    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db = SessionLocal()
    try:
        rag_api._ensure_rag_feedback_owner_column(db)
        db.commit()
    finally:
        db.close()

    cols = [c["name"] for c in inspect(engine).get_columns("rag_feedback")]
    assert "owner_id" in cols
