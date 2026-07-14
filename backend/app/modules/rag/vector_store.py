"""FAISS vector store creation and persistence.

Changed: Merged upstream Ollama embeddings with lazy, patchable FAISS loading.
Why: Docker RAG should use the configured local embedding model while tests
must still be able to monkeypatch ``app.modules.rag.vector_store.FAISS``.
Addresses: Import-time provider failures, broken mocks, and partial index writes.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import os
import shutil
import tempfile
import threading
from pathlib import Path
from typing import Any

from app.core.config import settings

try:
    from langchain_community.vectorstores import FAISS
except ImportError:  # pragma: no cover - exercised only when optional provider is absent
    FAISS = None

logger = logging.getLogger(__name__)
_rag_index_lock = threading.Lock()
_vector_store_cache: dict[int | None, Any] = {}
_vector_store_cache_lock = threading.Lock()

_HASH_ALGORITHM = "sha256"


def _index_hmac_key() -> bytes:
    return settings.SECRET_KEY.encode("utf-8")


def _compute_index_hash(index_path: str) -> str:
    sha = hashlib.sha256()
    for filename in sorted(os.listdir(index_path)):
        filepath = os.path.join(index_path, filename)
        if os.path.isfile(filepath):
            with open(filepath, "rb") as f:
                while True:
                    buf = f.read(65536)
                    if not buf:
                        break
                    sha.update(buf)
    return sha.hexdigest()


def _sign_hash(hash_value: str) -> str:
    return hmac.new(
        _index_hmac_key(),
        hash_value.encode("utf-8"),
        _HASH_ALGORITHM,
    ).hexdigest()


def _get_hash_path(index_path: str) -> str:
    return f"{index_path}.sha256"


def verify_index_integrity(index_path: str) -> None:
    hash_path = _get_hash_path(index_path)
    if not os.path.exists(hash_path):
        raise ValueError(
            f"Integrity hash not found at '{hash_path}'. "
            "The FAISS index may have been tampered with."
        )
    with open(hash_path) as f:
        stored = f.read().strip()
    parts = stored.split(":", 1)
    if len(parts) != 2:
        raise ValueError(f"Invalid integrity hash format at '{hash_path}'.")
    stored_hash, stored_sig = parts
    expected_sig = _sign_hash(stored_hash)
    if not hmac.compare_digest(stored_sig, expected_sig):
        raise ValueError(
            "Integrity hash signature verification failed at "
            f"'{hash_path}'. The hash file may have been tampered with."
        )
    current_hash = _compute_index_hash(index_path)
    if not hmac.compare_digest(current_hash, stored_hash):
        raise ValueError(
            f"FAISS index integrity check failed at '{index_path}'. "
            "The index contents do not match the stored hash."
        )


def store_index_integrity_hash(index_path: str) -> str:
    hash_value = _compute_index_hash(index_path)
    signature = _sign_hash(hash_value)
    hash_path = _get_hash_path(index_path)
    with open(hash_path, "w") as f:
        f.write(f"{hash_value}:{signature}")
    return hash_value


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
            store_index_integrity_hash(tmp_dir)

            verify_index_integrity(tmp_dir)
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
                store_index_integrity_hash(index_path)
                verify_index_integrity(index_path)
                faiss_cls.load_local(
                    index_path,
                    embeddings,
                    allow_dangerous_deserialization=True,
                )

            store_index_integrity_hash(index_path)

        finally:
            shutil.rmtree(tmp_dir, ignore_errors=True)

    with _vector_store_cache_lock:
        _vector_store_cache[user_id] = vector_store

    return vector_store


def load_vector_store(user_id: int | None = None) -> Any:
    """
    Load a FAISS index, reusing the in-process cached instance when available.

    Reingestion (``create_vector_store``) refreshes the cache for the same
    ``user_id``, so callers always see the latest index without paying the
    disk read and deserialization cost on every query.

    Args:
        user_id: Optional user ID for tenant-isolated index loading.

    Raises:
        FileNotFoundError: if the index has not been created yet.
    """
    with _vector_store_cache_lock:
        cached = _vector_store_cache.get(user_id)
    if cached is not None:
        return cached

    index_path = _get_index_path(user_id)
    if not os.path.exists(index_path):
        raise FileNotFoundError(
            f"FAISS index not found at '{index_path}'. "
            "The RAG module requires regulatory documents to be ingested first. "
            "Please contact your administrator or check the documentation for setup instructions."
        )

    verify_index_integrity(index_path)

    embeddings = get_embeddings()
    faiss_cls = _get_faiss_class()
    vector_store = faiss_cls.load_local(
        index_path, embeddings, allow_dangerous_deserialization=True
    )

    with _vector_store_cache_lock:
        _vector_store_cache[user_id] = vector_store

    return vector_store


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


def validate_vector_store_security() -> None:
    """Log a warning if existing FAISS indexes lack integrity verification."""
    for candidate in (settings.FAISS_INDEX_PATH, settings.FAISS_INDEX_BASE_PATH):
        index_path = Path(candidate)
        if index_path.exists() and index_path.is_dir():
            hash_file = index_path / "index.sha256"
            if not hash_file.exists():
                logger.warning(
                    "FAISS index at %s has no integrity verification. "
                    "Re-save the index to enable tamper detection.",
                    index_path,
                )
