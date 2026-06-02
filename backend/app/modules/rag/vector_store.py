"""FAISS vector store creation and persistence."""

import os
import shutil
import tempfile
import threading
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from langchain_community.embeddings import OllamaEmbeddings
from langchain_core.documents import Document
from app.core.config import settings
from .document_loader import load_documents_from_paths

_rag_index_lock = threading.Lock()


def get_embeddings():
    """Return the configured embeddings model."""
    '''return OpenAIEmbeddings(
        openai_api_key=settings.LLM_API_KEY,
        openai_api_base=settings.LLM_BASE_URL or None,
    )'''
    base = settings.LLM_BASE_URL or "http://ollama:11434"
    # OllamaEmbeddings wants the root URL, not the /v1 path
    if base.endswith("/v1"):
        base = base[:-3]
    return OllamaEmbeddings(model=settings.EMBEDDINGS_MODEL, base_url=base)


def create_vector_store(documents: list[Document]):
    """
    Build a FAISS index from a list of LangChain Document objects and persist it to disk.

    Args:
        documents: A list of loaded/chunked Document objects.

    Returns:
        The populated FAISS vector store.
    """
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
    embeddings = get_embeddings()
    return FAISS.load_local(
        index_path, embeddings, allow_dangerous_deserialization=True
    )


def check_index_exists():
    """Check if FAISS index exists on disk."""
    return os.path.exists(settings.FAISS_INDEX_PATH)
