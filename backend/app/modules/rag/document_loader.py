"""Document loader for ingesting regulatory PDFs from S3 or local disk."""

import logging
import os

from langchain_community.document_loaders import PyPDFLoader, S3DirectoryLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings

logger = logging.getLogger(__name__)

# Minimum file size in bytes — anything below this is considered an empty or placeholder file.
_MIN_PDF_SIZE_BYTES = 100


def load_documents_from_s3():
    """Load documents from the configured S3 bucket."""
    bucket = settings.S3_BUCKET_NAME
    if not bucket:
        raise ValueError("S3_BUCKET_NAME is not set in .env")
    loader = S3DirectoryLoader(bucket, prefix="docs/")
    documents = loader.load()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.RAG_CHUNK_SIZE,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP,
    )
    return splitter.split_documents(documents)


def load_documents_from_paths(file_paths: list[str]):
    """Load documents from a list of local PDF file paths.

    Validates each file before loading:
    - Skips files smaller than _MIN_PDF_SIZE_BYTES (raises ValueError with the path).
    - Wraps each PyPDFLoader call in try/except so a single corrupt file does not abort
      the entire batch.

    Raises:
        ValueError: When any file is smaller than the minimum byte threshold.
    """
    rejected: list[str] = []
    for path in file_paths:
        size = os.path.getsize(path)
        if size < _MIN_PDF_SIZE_BYTES:
            rejected.append(path)
    if rejected:
        raise ValueError(
            f"File(s) below minimum size ({_MIN_PDF_SIZE_BYTES} bytes): {rejected}"
        )

    documents = []
    for path in file_paths:
        try:
            loader = PyPDFLoader(path)
            documents.extend(loader.load())
        except Exception as exc:  # noqa: BLE001
            logger.warning("Skipping corrupt PDF %s: %s", path, exc)
            raise ValueError(
                f"Failed to parse PDF '{os.path.basename(path)}': {exc}"
            ) from exc

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.RAG_CHUNK_SIZE,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP,
    )
    return splitter.split_documents(documents)
