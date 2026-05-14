"""FAISS vector store creation and persistence."""

import os
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from .document_loader import load_documents_from_paths


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
    documents = load_documents_from_paths(file_paths)
    embeddings = get_embeddings()
    vector_store = FAISS.from_documents(documents, embeddings)
    vector_store.save_local(settings.FAISS_INDEX_PATH)
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
    embeddings = get_embeddings()
    return FAISS.load_local(
        index_path, embeddings, allow_dangerous_deserialization=True
    )


def check_index_exists():
    """Check if FAISS index exists on disk."""
    return os.path.exists(settings.FAISS_INDEX_PATH)
