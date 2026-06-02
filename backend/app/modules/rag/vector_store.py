"""FAISS vector store creation and persistence.

Changed: Kept LangChain provider imports lazy while preserving atomic FAISS index replacement.
Why: Tests and lightweight startup should not require provider packages until vector operations run.
Addresses: Import-time failures in mocked environments and partial index writes during ingestion.
"""

import os
import shutil
import tempfile
import threading

from app.core.config import settings
from .document_loader import load_documents_from_paths

_rag_index_lock = threading.Lock()


def get_embeddings():
    """Return the configured embeddings model."""
    from langchain_openai import OpenAIEmbeddings

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
    from langchain_community.vectorstores import FAISS

    documents = load_documents_from_paths(file_paths)
    embeddings = get_embeddings()
    vector_store = FAISS.from_documents(documents, embeddings)

    with _rag_index_lock:
        with tempfile.TemporaryDirectory(prefix="faiss_") as tmp_dir:
            vector_store.save_local(tmp_dir)
            FAISS.load_local(tmp_dir, embeddings, allow_dangerous_deserialization=True)
            if os.path.exists(settings.FAISS_INDEX_PATH):
                shutil.rmtree(settings.FAISS_INDEX_PATH, ignore_errors=True)
            shutil.move(tmp_dir, settings.FAISS_INDEX_PATH)

    return vector_store


def load_vector_store():
    """
    Load an existing FAISS index from disk.

    Raises:
        FileNotFoundError: if the index has not been created yet
    """
    index_path = settings.FAISS_INDEX_PATH
    if not os.path.exists(index_path):
        raise FileNotFoundError(
            f"FAISS index not found at '{index_path}'. "
            "The RAG module requires regulatory documents to be ingested first. "
            "Please contact your administrator or check the documentation for setup instructions."
        )
    from langchain_community.vectorstores import FAISS

    embeddings = get_embeddings()
    return FAISS.load_local(
        index_path, embeddings, allow_dangerous_deserialization=True
    )


def check_index_exists():
    """Check if FAISS index exists on disk."""
    return os.path.exists(settings.FAISS_INDEX_PATH)
