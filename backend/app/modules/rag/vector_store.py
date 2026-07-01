"""FAISS vector store creation and persistence.

Changed: Merged upstream Ollama embeddings with lazy, patchable FAISS loading.
Why: Docker RAG should use the configured local embedding model while tests
must still be able to monkeypatch ``app.modules.rag.vector_store.FAISS``.
Addresses: Import-time provider failures, broken mocks, and partial index writes.
"""

from __future__ import annotations

import logging
import os
import shutil
import tempfile
import threading
from typing import Any

from app.core.config import settings

try:
    from langchain_community.vectorstores import FAISS
except ImportError:  # pragma: no cover - exercised only when optional provider is absent
    FAISS = None

_rag_index_lock = threading.Lock()


def _get_faiss_class() -> Any:
    """Return the configured FAISS vector store class."""
    global FAISS
    if FAISS is None:
        from langchain_community.vectorstores import FAISS as LangChainFAISS

        FAISS = LangChainFAISS
    return FAISS


def get_embeddings() -> Any:
    """Return the configured embeddings model from the shared factory."""
    from app.modules.rag.embeddings import get_embeddings as _get_embeddings

    return _get_embeddings()


def _get_index_path(user_id: int | None = None) -> str:
    """Return the FAISS index path, scoped to a user when provided."""
    if user_id is not None:
        return os.path.join(settings.FAISS_INDEX_BASE_PATH, f"user_{user_id}")
    return settings.FAISS_INDEX_PATH


def create_vector_store(documents: list[Any], user_id: int | None = None) -> Any:
    """
    Build a FAISS index from LangChain Document objects and persist it to disk.

    Args:
        documents: Loaded and chunked LangChain Document objects.
        user_id: Optional user ID for tenant-isolated index storage.

    Returns:
        The populated FAISS vector store.
    """
    index_path = _get_index_path(user_id)
    os.makedirs(index_path, exist_ok=True)
    embeddings = get_embeddings()
    faiss_cls = _get_faiss_class()
    vector_store = faiss_cls.from_documents(documents, embeddings)

    with _rag_index_lock:
        tmp_dir = tempfile.mkdtemp(prefix="faiss_")

        try:
            vector_store.save_local(tmp_dir)

            faiss_cls.load_local(
                tmp_dir,
                embeddings,
                allow_dangerous_deserialization=True,
            )

            if os.path.exists(index_path):
                shutil.rmtree(index_path, ignore_errors=True)

            shutil.copytree(tmp_dir, index_path)
            if not os.path.exists(os.path.join(index_path, "index.faiss")):
                shutil.rmtree(index_path, ignore_errors=True)
                os.makedirs(index_path, exist_ok=True)
                vector_store.save_local(index_path)
                faiss_cls.load_local(
                    index_path,
                    embeddings,
                    allow_dangerous_deserialization=True,
                )

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)
    return vector_store


def load_vector_store(user_id: int | None = None) -> Any:
    """
    Load an existing FAISS index from disk.

    Args:
        user_id: Optional user ID for tenant-isolated index loading.

    Raises:
        FileNotFoundError: if the index has not been created yet.
    """
    index_path = _get_index_path(user_id)
    if not os.path.exists(index_path):
        raise FileNotFoundError(
            f"FAISS index not found at '{index_path}'. "
            "The RAG module requires regulatory documents to be ingested first. "
            "Please contact your administrator or check the documentation for setup instructions."
        )

    embeddings = get_embeddings()
    faiss_cls = _get_faiss_class()
    return faiss_cls.load_local(
        index_path, embeddings, allow_dangerous_deserialization=True
    )


def check_index_exists(user_id: int | None = None) -> bool:
    """Check if FAISS index exists on disk for the given user (or globally)."""
    return os.path.exists(_get_index_path(user_id))


def validate_embedding_consistency(user_id: int | None = None) -> None:
    """Validate that the existing FAISS index dimension matches the current embedding model."""
    index_path = _get_index_path(user_id)
    if not os.path.exists(index_path):
        return

    try:
        faiss_cls = _get_faiss_class()
        embeddings = get_embeddings()
        test_vector = embeddings.embed_query("dimension probe")
        model_dim = len(test_vector)

        store = faiss_cls.load_local(
            index_path,
            embeddings,
            allow_dangerous_deserialization=True,
        )
        index_dim = store.index.d
        if index_dim != model_dim:
            logger.warning(
                "FAISS index dimension (%d) doesn't match embedding model dimension (%d). "
                "Reingest documents with the current embedding model.",
                index_dim,
                model_dim,
            )
    except Exception as exc:
        logger.warning("Could not validate embedding consistency: %s", exc)
