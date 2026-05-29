"""FAISS vector store creation and persistence."""

import os
import shutil
import tempfile
import threading
import uuid
from contextlib import contextmanager
from pathlib import Path

from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from .document_loader import load_documents_from_paths

try:
    import fcntl
except ImportError:  # pragma: no cover - Windows fallback
    fcntl = None

_INDEX_REBUILD_LOCK = threading.Lock()
_INDEX_PATH_LOCK = threading.Lock()


def get_embeddings():
    """Return the configured embeddings model."""
    return OpenAIEmbeddings(
        openai_api_key=settings.LLM_API_KEY,
        openai_api_base=settings.LLM_BASE_URL or None,
    )


def create_vector_store(file_paths: list[str]):
    """
    Build a FAISS index from a list of local PDF paths and persist it to disk.

    Args:
        file_paths: Local paths to PDF documents to ingest

    Returns:
        The populated FAISS vector store
    """
    index_path = Path(settings.FAISS_INDEX_PATH)

    with _locked_index_path(index_path, _INDEX_REBUILD_LOCK, "rebuild"):
        staged_index_path = Path(
            tempfile.mkdtemp(
                prefix=f".{index_path.name}-staged-",
                dir=str(index_path.parent),
            )
        )

        try:
            documents = load_documents_from_paths(file_paths)
            embeddings = get_embeddings()
            vector_store = FAISS.from_documents(documents, embeddings)
            vector_store.save_local(str(staged_index_path))

            FAISS.load_local(
                str(staged_index_path),
                embeddings,
                allow_dangerous_deserialization=True,
            )
            with _locked_index_path(index_path, _INDEX_PATH_LOCK, "path"):
                _replace_index_directory(staged_index_path, index_path)
            return vector_store
        finally:
            _remove_path(staged_index_path)


def load_vector_store():
    """
    Load an existing FAISS index from disk.

    Raises:
        FileNotFoundError: if the index has not been created yet
    """
    index_path = Path(settings.FAISS_INDEX_PATH)
    with _locked_index_path(index_path, _INDEX_PATH_LOCK, "path"):
        if not os.path.exists(index_path):
            raise FileNotFoundError(
                f"FAISS index not found at '{index_path}'. "
                "The RAG module requires regulatory documents to be ingested first. "
                "Please contact your administrator or check the documentation for setup instructions."
            )
        embeddings = get_embeddings()
        return FAISS.load_local(
            str(index_path), embeddings, allow_dangerous_deserialization=True
        )


def check_index_exists():
    """Check if FAISS index exists on disk."""
    index_path = Path(settings.FAISS_INDEX_PATH)
    with _locked_index_path(index_path, _INDEX_PATH_LOCK, "path"):
        return os.path.exists(index_path)


def _replace_index_directory(staged_index_path: Path, index_path: Path) -> None:
    """Replace the live FAISS index with a validated staged index."""
    backup_path = None
    if index_path.exists():
        backup_path = index_path.with_name(
            f".{index_path.name}-backup-{uuid.uuid4().hex}"
        )
        index_path.rename(backup_path)

    try:
        staged_index_path.rename(index_path)
    except Exception:
        if backup_path and backup_path.exists() and not index_path.exists():
            backup_path.rename(index_path)
        raise
    else:
        if backup_path:
            _remove_path(backup_path)


def _remove_path(path: Path) -> None:
    """Remove a staged or backup FAISS path if it still exists."""
    if path.is_dir():
        shutil.rmtree(path, ignore_errors=True)
    elif path.exists():
        path.unlink()


@contextmanager
def _locked_index_path(index_path: Path, local_lock: threading.Lock, lock_name: str):
    """Serialize FAISS index operations across threads and worker processes."""
    index_path.parent.mkdir(parents=True, exist_ok=True)
    lock_file = None

    with local_lock:
        if fcntl is not None:
            lock_path = index_path.with_name(f".{index_path.name}.{lock_name}.lock")
            lock_file = open(lock_path, "w", encoding="utf-8")
            fcntl.flock(lock_file.fileno(), fcntl.LOCK_EX)

        try:
            yield
        finally:
            if lock_file is not None:
                try:
                    fcntl.flock(lock_file.fileno(), fcntl.LOCK_UN)
                finally:
                    lock_file.close()
