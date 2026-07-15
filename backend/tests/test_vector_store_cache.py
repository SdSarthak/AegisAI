"""Unit tests for the in-process FAISS vector store cache.

Covers the fix for the cold-start issue: load_vector_store() must not
re-read and re-deserialize the FAISS index from disk on every call once
it has already been loaded once in this process, and create_vector_store()
must refresh the cache so callers never see a stale index after reingestion.
"""

from unittest.mock import MagicMock, patch

import pytest

from app.modules.rag import vector_store


@pytest.fixture(autouse=True)
def clear_vector_store_cache():
    vector_store._vector_store_cache.clear()
    yield
    vector_store._vector_store_cache.clear()


def _fake_faiss_cls(load_return):
    faiss_cls = MagicMock()
    faiss_cls.load_local.return_value = load_return
    faiss_cls.from_documents.return_value = load_return
    return faiss_cls


def test_load_vector_store_only_reads_disk_once(tmp_path, monkeypatch):
    index_path = tmp_path / "index"
    index_path.mkdir()
    (index_path / "index.faiss").write_bytes(b"fake")

    monkeypatch.setattr(vector_store.settings, "FAISS_INDEX_PATH", str(index_path))
    fake_store = object()
    faiss_cls = _fake_faiss_cls(fake_store)

    with patch.object(vector_store, "_get_faiss_class", return_value=faiss_cls), \
         patch.object(vector_store, "get_embeddings", return_value=MagicMock()), \
         patch.object(vector_store, "_verify_index_integrity", return_value=True):
        first = vector_store.load_vector_store()
        second = vector_store.load_vector_store()

    assert first is fake_store
    assert second is fake_store
    faiss_cls.load_local.assert_called_once()


def test_create_vector_store_refreshes_cache_for_reingestion(tmp_path, monkeypatch):
    index_path = tmp_path / "index"
    monkeypatch.setattr(vector_store.settings, "FAISS_INDEX_PATH", str(index_path))

    stale_store = object()
    vector_store._vector_store_cache[None] = stale_store

    fresh_store = MagicMock()
    faiss_cls = _fake_faiss_cls(fresh_store)

    def fake_save_local(path):
        import os

        os.makedirs(path, exist_ok=True)
        with open(os.path.join(path, "index.faiss"), "wb") as f:
            f.write(b"fake")

    fresh_store.save_local.side_effect = fake_save_local

    with patch.object(vector_store, "_get_faiss_class", return_value=faiss_cls), \
         patch.object(vector_store, "get_embeddings", return_value=MagicMock()):
        result = vector_store.create_vector_store(documents=[MagicMock()])

    assert result is fresh_store
    assert vector_store._vector_store_cache[None] is fresh_store
    assert vector_store._vector_store_cache[None] is not stale_store
