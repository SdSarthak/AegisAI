"""Document loader for ingesting regulatory PDFs from S3 or local disk."""

import logging
import os
import pypdf.errors

from langchain_community.document_loaders import S3DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.core.config import settings

logger = logging.getLogger(__name__)


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
    - Rejects files smaller than ``settings.RAG_MIN_FILE_SIZE_BYTES``.
    - Wraps each :py:meth:`PyPDFLoader.load` call in try/except so a single
      corrupt file does not abort the entire batch.

    Raises:
        ValueError: When any file is too small or fails to parse.
    """
    min_size = settings.RAG_MIN_FILE_SIZE_BYTES
    rejected: list[str] = []
    for path in file_paths:
        try:
            size = os.path.getsize(path)
        except OSError as exc:
            rejected.append(f"{path} (access error: {exc})")
            continue
        if size < min_size:
            rejected.append(path)

    if rejected:
        raise ValueError(
            f"File(s) below minimum size ({min_size} bytes): {rejected}"
        )

    documents = []
    for path in file_paths:
        try:
            loader = PyPDFLoader(path)
            documents.extend(loader.load())
        except pypdf.errors.PdfReadError as exc:
            logger.warning(
                "Skipping corrupt/invalid PDF '%s': %s",
                os.path.basename(path),
                exc,
            )
            raise ValueError(
                f"Failed to parse PDF '{os.path.basename(path)}': {exc}"
            ) from exc
        except Exception as exc:
            logger.warning(
                "Unexpected error loading '%s': %s",
                os.path.basename(path),
                exc,
            )
            raise ValueError(
                f"Failed to load PDF '{os.path.basename(path)}': {exc}"
            ) from exc

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.RAG_CHUNK_SIZE,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP,
    )
    return splitter.split_documents(documents)
