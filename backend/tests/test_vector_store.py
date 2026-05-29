"""Tests for FAISS vector store persistence helpers."""

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from app.modules.rag import vector_store


def test_create_vector_store_stages_validates_and_replaces_live_index(
    tmp_path, monkeypatch
):
    """create_vector_store should never save directly into the live index path."""
    live_index_path = tmp_path / "faiss_index"
    live_index_path.mkdir()
    (live_index_path / "old.index").write_text("old")
    monkeypatch.setattr(
        vector_store.settings, "FAISS_INDEX_PATH", str(live_index_path)
    )

    fake_store = MagicMock()
    save_paths = []

    def save_local(path):
        save_path = Path(path)
        save_paths.append(save_path)
        save_path.mkdir(parents=True, exist_ok=True)
        (save_path / "index.faiss").write_text("new")

    fake_store.save_local.side_effect = save_local
    fake_embeddings = object()
    fake_documents = [MagicMock()]

    with (
        patch.object(
            vector_store,
            "load_documents_from_paths",
            return_value=fake_documents,
        ),
        patch.object(vector_store, "get_embeddings", return_value=fake_embeddings),
        patch.object(
            vector_store.FAISS,
            "from_documents",
            return_value=fake_store,
        ) as mock_from_documents,
        patch.object(vector_store.FAISS, "load_local") as mock_load_local,
    ):
        result = vector_store.create_vector_store(["policy.pdf"])

    assert result == fake_store
    assert save_paths
    assert save_paths[0] != live_index_path
    assert save_paths[0].parent == live_index_path.parent
    assert not save_paths[0].exists()
    assert (live_index_path / "index.faiss").read_text() == "new"
    assert not (live_index_path / "old.index").exists()
    if vector_store.fcntl is not None:
        assert (tmp_path / ".faiss_index.rebuild.lock").exists()
        assert (tmp_path / ".faiss_index.path.lock").exists()
    mock_from_documents.assert_called_once_with(fake_documents, fake_embeddings)
    mock_load_local.assert_called_once_with(
        str(save_paths[0]),
        fake_embeddings,
        allow_dangerous_deserialization=True,
    )


def test_create_vector_store_validation_failure_keeps_existing_index(
    tmp_path, monkeypatch
):
    """A staged index that cannot be reloaded must not replace the live index."""
    live_index_path = tmp_path / "faiss_index"
    live_index_path.mkdir()
    (live_index_path / "old.index").write_text("old")
    monkeypatch.setattr(
        vector_store.settings, "FAISS_INDEX_PATH", str(live_index_path)
    )

    fake_store = MagicMock()

    def save_local(path):
        staged_path = Path(path)
        staged_path.mkdir(parents=True, exist_ok=True)
        (staged_path / "index.faiss").write_text("new")

    fake_store.save_local.side_effect = save_local

    with (
        patch.object(vector_store, "load_documents_from_paths", return_value=[]),
        patch.object(vector_store, "get_embeddings", return_value=object()),
        patch.object(
            vector_store.FAISS,
            "from_documents",
            return_value=fake_store,
        ),
        patch.object(
            vector_store.FAISS,
            "load_local",
            side_effect=RuntimeError("bad staged index"),
        ),
    ):
        with pytest.raises(RuntimeError, match="bad staged index"):
            vector_store.create_vector_store(["policy.pdf"])

    assert (live_index_path / "old.index").read_text() == "old"
    assert not (live_index_path / "index.faiss").exists()
    assert list(tmp_path.glob(".faiss_index-staged-*")) == []


def test_create_vector_store_uses_rebuild_lock(tmp_path, monkeypatch):
    """The rebuild path should run while the local lock is held."""
    live_index_path = tmp_path / "faiss_index"
    monkeypatch.setattr(
        vector_store.settings, "FAISS_INDEX_PATH", str(live_index_path)
    )

    events = []

    class TrackingLock:
        def __enter__(self):
            events.append("lock-entered")

        def __exit__(self, exc_type, exc, tb):
            events.append("lock-exited")

    fake_store = MagicMock()

    def save_local(path):
        events.append("save-local")
        staged_path = Path(path)
        staged_path.mkdir(parents=True, exist_ok=True)
        (staged_path / "index.faiss").write_text("new")

    fake_store.save_local.side_effect = save_local
    monkeypatch.setattr(vector_store, "_INDEX_REBUILD_LOCK", TrackingLock())

    with (
        patch.object(
            vector_store,
            "load_documents_from_paths",
            side_effect=lambda _: events.append("load-documents") or [],
        ),
        patch.object(vector_store, "get_embeddings", return_value=object()),
        patch.object(
            vector_store.FAISS,
            "from_documents",
            side_effect=lambda *_: events.append("from-documents") or fake_store,
        ),
        patch.object(
            vector_store.FAISS,
            "load_local",
            side_effect=lambda *_args, **_kwargs: events.append("validate"),
        ),
    ):
        vector_store.create_vector_store(["policy.pdf"])

    assert events == [
        "lock-entered",
        "load-documents",
        "from-documents",
        "save-local",
        "validate",
        "lock-exited",
    ]


def test_load_vector_store_uses_index_lock(tmp_path, monkeypatch):
    """load_vector_store should not read during an unlocked rebuild swap."""
    live_index_path = tmp_path / "faiss_index"
    live_index_path.mkdir()
    monkeypatch.setattr(
        vector_store.settings, "FAISS_INDEX_PATH", str(live_index_path)
    )

    events = []

    class TrackingLock:
        def __enter__(self):
            events.append("lock-entered")

        def __exit__(self, exc_type, exc, tb):
            events.append("lock-exited")

    fake_embeddings = object()
    fake_store = MagicMock()
    monkeypatch.setattr(vector_store, "_INDEX_PATH_LOCK", TrackingLock())

    with (
        patch.object(vector_store, "get_embeddings", return_value=fake_embeddings),
        patch.object(
            vector_store.FAISS,
            "load_local",
            side_effect=lambda *_args, **_kwargs: events.append("load-local")
            or fake_store,
        ) as mock_load_local,
    ):
        result = vector_store.load_vector_store()

    assert result == fake_store
    assert events == ["lock-entered", "load-local", "lock-exited"]
    mock_load_local.assert_called_once_with(
        str(live_index_path),
        fake_embeddings,
        allow_dangerous_deserialization=True,
    )


def test_check_index_exists_uses_index_lock(tmp_path, monkeypatch):
    """check_index_exists should not inspect the path during a live swap."""
    live_index_path = tmp_path / "faiss_index"
    live_index_path.mkdir()
    monkeypatch.setattr(
        vector_store.settings, "FAISS_INDEX_PATH", str(live_index_path)
    )

    events = []

    class TrackingLock:
        def __enter__(self):
            events.append("lock-entered")

        def __exit__(self, exc_type, exc, tb):
            events.append("lock-exited")

    monkeypatch.setattr(vector_store, "_INDEX_PATH_LOCK", TrackingLock())

    assert vector_store.check_index_exists() is True
    assert events == ["lock-entered", "lock-exited"]
