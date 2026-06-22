"""Tests for RAG document_loader — file validation & error handling.

Covers:
- Empty / zero-byte PDF rejection
- Below-minimum-size rejection
- Corrupt / invalid PDF rejection
- Normal PDF loading (mocked loader)
- Multiple mixed files (valid + invalid)
- Configurable threshold via settings
"""

import logging
import os
import tempfile
from unittest.mock import MagicMock, patch

import pytest

from app.modules.rag import document_loader

# Silence noisy dependency loggers during tests
logging.getLogger("langchain_community").setLevel(logging.ERROR)
logging.getLogger("pypdf").setLevel(logging.ERROR)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_dir():
    """Create a temporary directory and clean it up afterwards."""
    with tempfile.TemporaryDirectory() as d:
        yield d


def _write_file(tmp_dir: str, name: str, data: bytes) -> str:
    """Write *data* to *name* inside *tmp_dir* and return the abs path."""
    path = os.path.join(tmp_dir, name)
    with open(path, "wb") as f:
        f.write(data)
    return os.path.abspath(path)


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


class TestLoadDocumentsFromPaths:
    """Validate document_loader.load_documents_from_paths guards."""

    # --- Empty / too-small files ---

    def test_empty_pdf_raises(self, tmp_dir):
        """A 0-byte file should raise ValueError."""
        path = _write_file(tmp_dir, "empty.pdf", b"")
        with pytest.raises(ValueError, match=r"below minimum size.*empty\.pdf"):
            document_loader.load_documents_from_paths([path])

    def test_small_pdf_raises(self, tmp_dir):
        """A file below RAG_MIN_FILE_SIZE_BYTES should raise ValueError."""
        path = _write_file(tmp_dir, "tiny.pdf", b"dummy")
        with pytest.raises(ValueError, match="below minimum size"):
            document_loader.load_documents_from_paths([path])

    def test_threshold_is_configurable(self, tmp_dir, monkeypatch):
        """The threshold should come from settings, not a hard-coded constant."""
        from app.core.config import settings as s

        monkeypatch.setattr(s, "RAG_MIN_FILE_SIZE_BYTES", 5)

        # 3 bytes — below threshold 5 → raises
        path = _write_file(tmp_dir, "small.pdf", b"abc")
        with pytest.raises(ValueError, match="below minimum size"):
            document_loader.load_documents_from_paths([path])

    def test_multiple_empty_files_list_all(self, tmp_dir):
        """All rejected files should be listed, not just the first."""
        p1 = _write_file(tmp_dir, "a.pdf", b"")
        p2 = _write_file(tmp_dir, "b.pdf", b"x")
        p3 = _write_file(tmp_dir, "c.pdf", b"")

        paths = [p1, p2, p3]
        with pytest.raises(ValueError) as exc_info:
            document_loader.load_documents_from_paths(paths)
        err_msg = str(exc_info.value)
        # The error should mention "below minimum size" and contain filenames
        assert "below minimum size" in err_msg
        # a.pdf and c.pdf should both be in the list
        assert "a.pdf" in err_msg
        assert "c.pdf" in err_msg

    # --- Corrupt / invalid PDF (ensure data >= 100 bytes) ---

    def test_corrupt_pdf_raises(self, tmp_dir):
        """A file >= min_size but invalid as PDF should raise ValueError."""
        path = _write_file(
            tmp_dir,
            "corrupt.pdf",
            b"This is not a PDF at all, just random text "
            b"bytes\x00\x01\x02\x03\x04\x05\x06\x07\x08",
        )
        # Pad to >= 100 bytes
        path = _write_file(
            tmp_dir,
            "corrupt2.pdf",
            b"This is not a PDF at all, just random text bytes "
            b"that exceeds one hundred bytes to pass the size gate "
            b"and then fail during parsing. "
            b"More filler to make it long enough. "
            b"Extra padding for good measure.",
        )
        with pytest.raises(ValueError, match="Failed to parse PDF"):
            document_loader.load_documents_from_paths([path])

    def test_corrupt_pdf_logs_warning(self, tmp_dir, caplog):
        """A corrupt PDF should emit a warning log."""
        path = _write_file(
            tmp_dir,
            "bad.pdf",
            b"Not a PDF at all, just random text bytes that exceeds "
            b"one hundred bytes to pass the size gate and then fail "
            b"during parsing. More filler to make it long enough. "
            b"Extra padding for good measure.",
        )
        with caplog.at_level(logging.WARNING):
            with pytest.raises(ValueError, match="Failed to parse PDF"):
                document_loader.load_documents_from_paths([path])
        assert "corrupt" in caplog.text.lower() or "parse" in caplog.text.lower()

    # --- OSError / permission ---

    def test_unreadable_file_raises(self, tmp_dir, monkeypatch):
        """A file that raises OSError on stat should be rejected."""
        fake_path = os.path.join(tmp_dir, "ghost.pdf")
        with monkeypatch.context() as m:
            m.setattr(os.path, "getsize", MagicMock(side_effect=OSError("nope")))
            with pytest.raises(ValueError, match="access error: nope"):
                document_loader.load_documents_from_paths([fake_path])

    # --- Normal valid PDF (mocked loader) ---

    def test_valid_pdf_returns_chunks(self, tmp_dir):
        """A valid path (>= min_size) should call PyPDFLoader normally."""
        from langchain_core.documents import Document

        # Create a file that passes the size gate
        path = _write_file(
            tmp_dir,
            "valid.pdf",
            b"%PDF-1.4\n" + b"x" * 200,  # > 100 bytes
        )

        mock_doc = MagicMock(spec=Document)
        mock_doc.page_content = "some text"
        mock_doc.metadata = {"source": path}

        with patch("app.modules.rag.document_loader.PyPDFLoader") as MockLoader:
            instance = MagicMock()
            instance.load.return_value = [mock_doc]
            MockLoader.return_value = instance

            result = document_loader.load_documents_from_paths([path])

        # Should have called the loader once
        MockLoader.assert_called_once_with(path)
        instance.load.assert_called_once()
        assert len(result) == 1

    def test_single_corrupt_file_raises_value_error(self, tmp_dir):
        """If ONE file is corrupt (passes size gate), it should raise ValueError."""
        from langchain_core.documents import Document

        valid_path = _write_file(
            tmp_dir, "valid.pdf", b"%PDF-1.4\n" + b"x" * 200
        )
        corrupt_path = _write_file(
            tmp_dir,
            "bad.pdf",
            b"Not a PDF at all, just random text bytes that exceeds "
            b"one hundred bytes to pass the size gate and then fail "
            b"during parsing. More filler to make it long enough. "
            b"Extra padding for good measure.",
        )

        # Current implementation fails fast on first corrupt file after size check.
        # Verify it raises correctly.
        with pytest.raises(ValueError, match="Failed to parse PDF"):
            document_loader.load_documents_from_paths([valid_path, corrupt_path])
