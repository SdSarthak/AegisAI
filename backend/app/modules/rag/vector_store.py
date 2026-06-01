"""FAISS vector store creation and persistence."""

import os
import shutil
import tempfile
import threading
import uuid
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings
from app.core.config import settings
from .document_loader import load_documents_from_paths

# Lock to serialize concurrent FAISS builds
rag_index_lock = threading.Lock()
# Fast lock for atomic directory swaps and index loads
rag_swap_lock = threading.Lock()


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
    with rag_index_lock:
        documents = load_documents_from_paths(file_paths)
        embeddings = get_embeddings()
        vector_store = FAISS.from_documents(documents, embeddings)
        
        index_path = settings.FAISS_INDEX_PATH
        parent_dir = os.path.dirname(os.path.abspath(index_path))
        os.makedirs(parent_dir, exist_ok=True)
        
        tmp_dir = tempfile.mkdtemp(dir=parent_dir, prefix="faiss_index_tmp_")
        tmp_dir_moved = False
        
        try:
            vector_store.save_local(tmp_dir)
            
            # Validate that the built index loads correctly
            try:
                FAISS.load_local(tmp_dir, embeddings, allow_dangerous_deserialization=True)
            except Exception as e:
                raise ValueError(f"Failed to validate built FAISS index: {e}")
            
            # Perform a safe atomic swap
            with rag_swap_lock:
                if os.path.exists(index_path):
                    backup_path = os.path.join(parent_dir, f"faiss_index_old_{uuid.uuid4().hex}")
                    try:
                        os.rename(index_path, backup_path)
                        os.rename(tmp_dir, index_path)
                        tmp_dir_moved = True
                    except Exception as rename_err:
                        if os.path.exists(backup_path) and not os.path.exists(index_path):
                            os.rename(backup_path, index_path)
                        raise rename_err
                    finally:
                        if os.path.exists(backup_path):
                            shutil.rmtree(backup_path, ignore_errors=True)
                else:
                    os.rename(tmp_dir, index_path)
                    tmp_dir_moved = True
        finally:
            if not tmp_dir_moved and os.path.exists(tmp_dir):
                shutil.rmtree(tmp_dir, ignore_errors=True)
                
        return vector_store


def load_vector_store():
    """
    Load an existing FAISS index from disk.

    Raises:
        FileNotFoundError: if the index has not been created yet
    """
    with rag_swap_lock:
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
    with rag_swap_lock:
        return os.path.exists(settings.FAISS_INDEX_PATH)

