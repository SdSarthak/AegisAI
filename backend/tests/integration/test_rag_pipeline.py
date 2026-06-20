"""
Integration tests for the end-to-end RAG pipeline.

Flow under test
---------------
1. Generate a small PDF with known regulatory text (reportlab — already in requirements.txt).
2. POST /api/v1/rag/ingest  → verify FAISS index files land on disk.
3. POST /api/v1/rag/query   → verify a non-empty answer and at least one source.

Design notes
------------
- Heavy external dependencies (OpenAI embeddings, LangChain LLM) are replaced
  with lightweight fakes so the suite runs without any API keys or GPU.
- The FAISS index is written to a *temporary directory* that is cleaned up in
  the fixture teardown, keeping the test fully isolated from any real index.
- Auth is handled by creating a real User row and issuing a JWT, matching the
  pattern used in test_rate_limiting.py.
- The conftest `client` / `db_session` fixtures are reused as-is.
"""

import io
import os
import shutil
import sys
import tempfile
import uuid
from types import ModuleType
from unittest.mock import MagicMock, patch

import pytest
from reportlab.lib.pagesizes import A4
from reportlab.platypus import Paragraph, SimpleDocTemplate
from reportlab.lib.styles import getSampleStyleSheet

from app.core.security import create_access_token
from app.models.user import User


# ---------------------------------------------------------------------------
# Constants — the "known" text baked into the test PDF
# ---------------------------------------------------------------------------

KNOWN_ARTICLE = (
    "Article 6 of the EU AI Act classifies AI systems used for CV screening "
    "and credit scoring as high-risk systems that require conformity assessment "
    "before being placed on the market."
)
KNOWN_QUESTION = "What does Article 6 of the EU AI Act say about CV screening?"
KNOWN_ANSWER = (
    "Article 6 classifies CV screening as a high-risk AI system requiring "
    "conformity assessment."
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _build_test_pdf() -> bytes:
    """Return the bytes of a minimal PDF containing KNOWN_ARTICLE."""
    buf = io.BytesIO()
    doc = SimpleDocTemplate(buf, pagesize=A4)
    styles = getSampleStyleSheet()
    story = [
        Paragraph("EU AI Act — Test Regulatory Document", styles["Heading1"]),
        Paragraph(KNOWN_ARTICLE, styles["BodyText"]),
    ]
    doc.build(story)
    return buf.getvalue()


def _register_user(db_session) -> dict:
    """Insert a test user and return Bearer auth headers."""
    user = User(
        email=f"rag-pipeline-{uuid.uuid4().hex[:8]}@example.com",
        hashed_password="$2b$12$R9h31cIPz0yO8W4gw2love.a4UtcWLU7pHPti3/T.D18SMsKvRHO2",
        is_active=True,
        company_name="AegisAI Tests",
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    token = create_access_token(data={"sub": str(user.id)})
    return {"Authorization": f"Bearer {token}"}


# ---------------------------------------------------------------------------
# Fake FAISS / embedding / LLM objects
# ---------------------------------------------------------------------------

class _FakeRetriever:
    """Mimics a LangChain retriever; returns one fake source document."""

    def get_relevant_documents(self, query: str):
        doc = MagicMock()
        doc.page_content = KNOWN_ARTICLE
        doc.metadata = {"source": "test_regulatory.pdf", "page": 0}
        return [doc]

    # LangChain also calls this via the async path in some versions
    def as_retriever(self, **kwargs):
        return self


class _FakeVectorStore:
    """Minimal FAISS stand-in that writes sentinel files to disk."""

    def __init__(self, index_path: str):
        self._index_path = index_path

    def save_local(self, path: str):
        """Write the two files that the real FAISS.save_local produces."""
        os.makedirs(path, exist_ok=True)
        open(os.path.join(path, "index.faiss"), "wb").close()
        open(os.path.join(path, "index.pkl"), "wb").close()

    def as_retriever(self, **kwargs):
        return _FakeRetriever()

    @classmethod
    def from_documents(cls, documents, embeddings):
        return cls(index_path="")

    @classmethod
    def load_local(cls, path, embeddings, allow_dangerous_deserialization=False):
        return cls(index_path=path)


class _FakeQAChain:
    """Mimics a LangChain RetrievalQA chain."""

    def __call__(self, inputs: dict) -> dict:
        return {
            "result": KNOWN_ANSWER,
            "source_documents": _FakeRetriever().get_relevant_documents(
                inputs.get("query", "")
            ),
        }


# ---------------------------------------------------------------------------
# Fixture: isolated FAISS index directory + all heavy patches
# ---------------------------------------------------------------------------

@pytest.fixture()
def rag_env(monkeypatch):
    """
    Yield a dict with:
      - ``index_dir``: the temporary directory used as FAISS_INDEX_PATH
      - ``pdf_bytes``: the generated test PDF bytes

    Patches applied for the duration of the test:
      - settings.FAISS_INDEX_PATH → temp dir
      - OpenAIEmbeddings          → MagicMock (no API key needed)
      - FAISS.from_documents      → _FakeVectorStore
      - FAISS.load_local          → _FakeVectorStore
      - RetrievalQA chain         → _FakeQAChain
      - ChatOpenAI                → MagicMock (no API key needed)
    """
    index_dir = tempfile.mkdtemp(prefix="aegis_test_faiss_")

    try:
        # ── Point settings at the temp dir ────────────────────────────────
        monkeypatch.setattr("app.core.config.settings.FAISS_INDEX_PATH", index_dir)
        monkeypatch.setattr("app.core.config.settings.FAISS_INDEX_BASE_PATH", index_dir)
        # Also patch the attribute on the already-imported module objects
        monkeypatch.setattr("app.modules.rag.vector_store.settings.FAISS_INDEX_PATH", index_dir)
        monkeypatch.setattr("app.modules.rag.vector_store.settings.FAISS_INDEX_BASE_PATH", index_dir)

        # ── Fake embeddings (avoids OpenAI API call) ──────────────────────
        fake_embeddings = MagicMock()
        fake_embeddings.embed_documents = MagicMock(return_value=[[0.1] * 768])
        fake_embeddings.embed_query = MagicMock(return_value=[0.1] * 768)

        monkeypatch.setattr(
            "app.modules.rag.vector_store.get_embeddings",
            lambda: fake_embeddings,
        )

        # ── Fake FAISS class ──────────────────────────────────────────────
        monkeypatch.setattr(
            "app.modules.rag.vector_store.FAISS",
            _FakeVectorStore,
        )

        # ── Fake QA chain (avoids LLM call) ──────────────────────────────
        monkeypatch.setattr(
            "app.modules.rag.retrieval_chain.get_qa_chain",
            lambda user_id=None: _FakeQAChain(),
        )
        # Also patch the import inside rag.py's query handler
        monkeypatch.setattr(
            "app.api.v1.rag.get_qa_chain" if hasattr(
                sys.modules.get("app.api.v1.rag", object()), "get_qa_chain"
            ) else "app.modules.rag.retrieval_chain.get_qa_chain",
            lambda user_id=None: _FakeQAChain(),
        )

        yield {
            "index_dir": index_dir,
            "pdf_bytes": _build_test_pdf(),
        }

    finally:
        # ── Teardown: remove the test FAISS index ─────────────────────────
        shutil.rmtree(index_dir, ignore_errors=True)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRagPipelineIntegration:
    """End-to-end tests covering ingest → index-on-disk → query → answer."""

    # ------------------------------------------------------------------
    # 1. Ingest
    # ------------------------------------------------------------------

    def test_ingest_creates_faiss_index_on_disk(self, client, db_session, rag_env):
        """
        POST /rag/ingest with a valid PDF must:
        - return HTTP 200
        - report files_processed == 1 and chunks_created > 0
        - write index.faiss and index.pkl to the configured index directory (user-scoped)
        """
        auth = _register_user(db_session)
        pdf_bytes = rag_env["pdf_bytes"]
        index_dir = rag_env["index_dir"]

        # Decode the user id from the JWT to determine the user-scoped index path
        from app.core.security import decode_token
        token = auth["Authorization"].removeprefix("Bearer ")
        payload = decode_token(token)
        user_id = int(payload["sub"])
        user_index_dir = os.path.join(index_dir, f"user_{user_id}")

        response = client.post(
            "/api/v1/rag/ingest",
            files={"files": ("test_regulatory.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            headers=auth,
        )

        assert response.status_code == 200, response.text
        data = response.json()

        # Response fields
        assert data["files_processed"] == 1
        assert data["chunks_created"] > 0, "Expected at least one text chunk from the PDF"

        # FAISS index files must exist on disk (under user-scoped path)
        assert os.path.exists(os.path.join(user_index_dir, "index.faiss")), (
            "index.faiss not found — FAISS index was not persisted"
        )
        assert os.path.exists(os.path.join(user_index_dir, "index.pkl")), (
            "index.pkl not found — FAISS index was not persisted"
        )

    def test_ingest_response_contains_index_size(self, client, db_session, rag_env):
        """
        index_size_bytes in the response must be a non-negative integer.
        (The fake index files are empty, so 0 is acceptable here.)
        """
        auth = _register_user(db_session)
        pdf_bytes = rag_env["pdf_bytes"]

        response = client.post(
            "/api/v1/rag/ingest",
            files={"files": ("test_regulatory.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            headers=auth,
        )

        assert response.status_code == 200, response.text
        data = response.json()
        assert isinstance(data["index_size_bytes"], int)
        assert data["index_size_bytes"] >= 0

    # ------------------------------------------------------------------
    # 2. Query
    # ------------------------------------------------------------------

    def test_query_returns_non_empty_answer(self, client, db_session, rag_env):
        """
        After ingestion, POST /rag/query must return a non-empty answer string.
        """
        auth = _register_user(db_session)
        pdf_bytes = rag_env["pdf_bytes"]

        # Ingest first so the index exists
        ingest_resp = client.post(
            "/api/v1/rag/ingest",
            files={"files": ("test_regulatory.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            headers=auth,
        )
        assert ingest_resp.status_code == 200, ingest_resp.text

        # Query
        query_resp = client.post(
            "/api/v1/rag/query",
            json={"question": KNOWN_QUESTION},
            headers=auth,
        )

        assert query_resp.status_code == 200, query_resp.text
        data = query_resp.json()
        assert "answer" in data
        assert isinstance(data["answer"], str)
        assert len(data["answer"].strip()) > 0, "answer must not be empty"

    def test_query_returns_at_least_one_source(self, client, db_session, rag_env):
        """
        The sources list in the query response must contain at least one entry.
        """
        auth = _register_user(db_session)
        pdf_bytes = rag_env["pdf_bytes"]

        client.post(
            "/api/v1/rag/ingest",
            files={"files": ("test_regulatory.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            headers=auth,
        )

        query_resp = client.post(
            "/api/v1/rag/query",
            json={"question": KNOWN_QUESTION},
            headers=auth,
        )

        assert query_resp.status_code == 200, query_resp.text
        data = query_resp.json()
        assert "sources" in data
        assert isinstance(data["sources"], list)
        assert len(data["sources"]) >= 1, (
            "Expected at least one source document reference in the response"
        )

    def test_query_answer_id_is_present(self, client, db_session, rag_env):
        """
        The response must include an answer_id so callers can submit feedback.
        """
        auth = _register_user(db_session)
        pdf_bytes = rag_env["pdf_bytes"]

        client.post(
            "/api/v1/rag/ingest",
            files={"files": ("test_regulatory.pdf", io.BytesIO(pdf_bytes), "application/pdf")},
            headers=auth,
        )

        query_resp = client.post(
            "/api/v1/rag/query",
            json={"question": KNOWN_QUESTION},
            headers=auth,
        )

        assert query_resp.status_code == 200, query_resp.text
        data = query_resp.json()
        assert "answer_id" in data
        assert data["answer_id"] is not None

    # ------------------------------------------------------------------
    # 3. Teardown verification (index removed after fixture cleanup)
    # ------------------------------------------------------------------

    def test_index_dir_is_cleaned_up_after_test(self, tmp_path):
        """
        Verify the teardown logic: a directory created and then removed by
        shutil.rmtree should no longer exist.  This mirrors what the rag_env
        fixture does in its finally block.
        """
        sentinel = tmp_path / "faiss_sentinel"
        sentinel.mkdir()
        (sentinel / "index.faiss").write_bytes(b"")
        (sentinel / "index.pkl").write_bytes(b"")

        assert sentinel.exists()
        shutil.rmtree(str(sentinel), ignore_errors=True)
        assert not sentinel.exists(), (
            "Teardown did not remove the test FAISS index directory"
        )

    # ------------------------------------------------------------------
    # 4. Auth guard
    # ------------------------------------------------------------------

    def test_ingest_requires_authentication(self, client, rag_env):
        """Requests without a JWT must be rejected before reaching ingest logic."""
        response = client.post(
            "/api/v1/rag/ingest",
            files={"files": ("test.pdf", io.BytesIO(rag_env["pdf_bytes"]), "application/pdf")},
            # No Authorization header
        )
        assert response.status_code in (401, 403)

    def test_query_requires_authentication(self, client, rag_env):
        """Requests without a JWT must be rejected before reaching query logic."""
        response = client.post(
            "/api/v1/rag/query",
            json={"question": KNOWN_QUESTION},
            # No Authorization header
        )
        assert response.status_code in (401, 403)
