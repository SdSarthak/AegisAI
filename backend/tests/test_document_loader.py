"""
Tests for backend/app/modules/rag/document_loader.py file-size validation.

Covers load_documents_from_paths() minimum-file-size check and parse-error handling.
"""

from __future__ import annotations

import os
import pytest
from unittest.mock import patch, MagicMock

# Set required env vars before importing the document_loader module.
os.environ.setdefault("DATABASE_URL", "sqlite:///:memory:")
os.environ.setdefault("SECRET_KEY", "test-secret-key")
os.environ.setdefault("REDIS_URL", "")
os.environ.setdefault("RAG_CHUNK_SIZE", "1000")
os.environ.setdefault("RAG_CHUNK_OVERLAP", "200")

from app.modules.rag.document_loader import (
    load_documents_from_paths,
    _MIN_PDF_SIZE_BYTES,
)


class TestLoadDocumentsFromPaths:
    """Unit tests for load_documents_from_paths() file validation."""

    def test_file_below_minimum_size_raises_valueerror(self, tmp_path):
        """File smaller than _MIN_PDF_SIZE_BYTES raises ValueError with path."""
        small_file = tmp_path / "tiny.pdf"
        small_file.write_bytes(b"%PDF-small-placeholder")

        with pytest.raises(ValueError, match=str(small_file)):
            load_documents_from_paths([str(small_file)])

    def test_file_below_minimum_size_mention_bytes_in_error(self, tmp_path):
        """Error message should mention the byte threshold."""
        small_file = tmp_path / "tiny.pdf"
        small_file.write_bytes(b"x")
        threshold = _MIN_PDF_SIZE_BYTES

        with pytest.raises(ValueError, match=str(threshold)):
            load_documents_from_paths([str(small_file)])

    def test_multiple_files_one_below_minimum_raises_on_small_file(self, tmp_path):
        """When one of several files is too small, error names that file."""
        valid_file = tmp_path / "valid.pdf"
        valid_file.write_bytes(b"A" * (_MIN_PDF_SIZE_BYTES + 100))

        small_file = tmp_path / "tiny.pdf"
        small_file.write_bytes(b"x")

        with pytest.raises(ValueError, match=str(small_file)):
            load_documents_from_paths([str(valid_file), str(small_file)])

    @patch("app.modules.rag.document_loader.RecursiveCharacterTextSplitter")
    def test_corrupt_pdf_raises_valueerror_with_filename(
        self, mock_splitter_cls, tmp_path
    ):
        """Corrupt/unparseable PDF raises ValueError with the basename in the message."""
        mock_splitter_cls.return_value = MagicMock(split_documents=MagicMock(return_value=[]))
        corrupt_file = tmp_path / "corrupt.pdf"
        corrupt_file.write_bytes(b"%PDF-1.0\n%corrupt bytes")

        # Patch PyPDFLoader to raise an exception
        with patch(
            "app.modules.rag.document_loader.PyPDFLoader"
        ) as mock_loader_cls:
            mock_loader_cls.return_value.load.side_effect = RuntimeError("No pages found")
            with pytest.raises(ValueError, match="corrupt.pdf"):
                load_documents_from_paths([str(corrupt_file)])

    @patch("app.modules.rag.document_loader.RecursiveCharacterTextSplitter")
    @patch("app.modules.rag.document_loader.PyPDFLoader")
    def test_valid_file_returns_split_documents(
        self, mock_loader_cls, mock_splitter_cls, tmp_path
    ):
        """Valid file above minimum size returns split documents."""
        valid_file = tmp_path / "valid.pdf"
        valid_file.write_bytes(b"%PDF-1.4\n" + b"A" * _MIN_PDF_SIZE_BYTES)

        mock_pages = [MagicMock(page_content="Chunk 1"), MagicMock(page_content="Chunk 2")]
        mock_loader_cls.return_value.load.return_value = mock_pages

        mock_splitter = MagicMock()
        mock_splitter.split_documents.return_value = ["split_chunk_1", "split_chunk_2"]
        mock_splitter_cls.return_value = mock_splitter

        result = load_documents_from_paths([str(valid_file)])

        assert result == ["split_chunk_1", "split_chunk_2"]
        mock_loader_cls.return_value.load.assert_called_once()
        mock_splitter.split_documents.assert_called_once_with(mock_pages)

    @patch("app.modules.rag.document_loader.RecursiveCharacterTextSplitter")
    @patch("app.modules.rag.document_loader.PyPDFLoader")
    def test_multiple_valid_files_processed_in_order(
        self, mock_loader_cls, mock_splitter_cls, tmp_path
    ):
        """Multiple valid files are each loaded and their chunks concatenated."""
        files = []
        for i in range(3):
            f = tmp_path / f"doc{i}.pdf"
            f.write_bytes(b"%PDF-1.4\n" + b"B" * _MIN_PDF_SIZE_BYTES)
            files.append(str(f))

        # Each load() call returns chunks from one file
        mock_loader_cls.return_value.load.side_effect = [
            [MagicMock(page_content=f"Chunk {i}") for i in range(3)]
            for _ in range(3)
        ]
        mock_splitter = MagicMock()
        mock_splitter.split_documents.return_value = ["final_chunk"]
        mock_splitter_cls.return_value = mock_splitter

        result = load_documents_from_paths(files)

        assert mock_loader_cls.call_count == 3
        # Splitter is created once and called once at the end with all concatenated docs
        assert mock_splitter.split_documents.call_count == 1

    def test_minimum_size_constant_is_reasonable(self):
        """_MIN_PDF_SIZE_BYTES should be a positive value that is non-zero."""
        assert _MIN_PDF_SIZE_BYTES > 0
        # A reasonable PDF minimum should be at least 50 bytes
        assert _MIN_PDF_SIZE_BYTES >= 50
