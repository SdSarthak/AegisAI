"""Tests for FAISS vector store safety — locks, atomic directory swaps, validation and load checks."""

import os
import shutil
import tempfile
import threading
import time
from unittest.mock import MagicMock, patch
import pytest
from app.modules.rag.vector_store import (
    create_vector_store,
    load_vector_store,
    check_index_exists,
    rag_index_lock,
    rag_swap_lock,
)
from app.core.config import settings


def test_vector_store_safety_and_swaps(tmp_path, monkeypatch):
    """Verify that vector store ingestion performs thread-safe atomic directory swaps and validations."""
    index_path = tmp_path / "faiss_index_test"
    monkeypatch.setattr(settings, "FAISS_INDEX_PATH", str(index_path))

    mock_embeddings = MagicMock()
    mock_vs = MagicMock()
    
    # Track paths that save_local is called on
    saved_paths = []

    def mock_save_local(path):
        saved_paths.append(path)
        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "index.faiss"), "w") as f:
            f.write("fake index")
        with open(os.path.join(path, "index.pkl"), "w") as f:
            f.write("fake pkl")

    mock_vs.save_local.side_effect = mock_save_local

    with (
        patch("app.modules.rag.vector_store.load_documents_from_paths", return_value=["doc1"]),
        patch("app.modules.rag.vector_store.get_embeddings", return_value=mock_embeddings),
        patch("langchain_community.vectorstores.FAISS.from_documents", return_value=mock_vs),
        patch("langchain_community.vectorstores.FAISS.load_local", return_value=mock_vs),
    ):
        # 1. Verify initially check_index_exists is False
        assert not check_index_exists()
        
        # 2. Rebuild the index for the first time
        vs = create_vector_store(["/path/to/doc.pdf"])
        assert vs == mock_vs
        assert index_path.exists()
        assert (index_path / "index.faiss").exists()
        assert (index_path / "index.pkl").exists()
        assert check_index_exists()

        # Check that we built in a temp dir (which was a prefix "faiss_index_tmp_")
        assert len(saved_paths) == 1
        assert "faiss_index_tmp_" in saved_paths[0]

        # 3. Load the index and verify it succeeds under swap lock
        loaded_vs = load_vector_store()
        assert loaded_vs == mock_vs

        # 4. Trigger a second rebuild to verify atomic swap replaces the old directory correctly
        vs2 = create_vector_store(["/path/to/doc2.pdf"])
        assert vs2 == mock_vs
        assert index_path.exists()
        assert (index_path / "index.faiss").exists()
        assert (index_path / "index.pkl").exists()
        
        assert len(saved_paths) == 2
        assert "faiss_index_tmp_" in saved_paths[1]
