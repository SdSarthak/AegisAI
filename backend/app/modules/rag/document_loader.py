"""Utilities to load documents for RAG pipelines."""

from __future__ import annotations

from typing import TYPE_CHECKING

from backend.app.core.config import settings

# LangChain has moved many integrations to `langchain_community`.
# Use community imports when available, and fall back to legacy paths.
try:
    # Newer LangChain layouts
    from langchain_community.document_loaders import PyPDFLoader
    from langchain_community.document_loaders.s3_directory import S3DirectoryLoader
    try:
        # Most common community location
        from langchain_community.text_splitters import RecursiveCharacterTextSplitter
    except ImportError:  # pragma: no cover
        # Some versions ship splitters as a separate package
        from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:  # pragma: no cover
    # Legacy fallback
    from langchain.document_loaders import PyPDFLoader
    from langchain.document_loaders.s3_directory import S3DirectoryLoader
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    except ImportError:  # pragma: no cover
        from langchain_text_splitters import RecursiveCharacterTextSplitter



def load_documents_from_s3():
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
    documents = []
    for path in file_paths:
        loader = PyPDFLoader(path)
        documents.extend(loader.load())

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.RAG_CHUNK_SIZE,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP,
    )
    return splitter.split_documents(documents)

