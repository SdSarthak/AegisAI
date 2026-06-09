"""Document loader for ingesting regulatory PDFs from S3 or local disk."""

import os
from langchain_community.document_loaders import S3DirectoryLoader, PyPDFLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.core.config import settings


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
    """Load documents from a list of local PDF file paths."""
    documents = []
    from langchain_community.document_loaders import TextLoader
    for path in file_paths:
        ext = os.path.splitext(path)[1].lower()
        if ext == '.pdf':
            loader = PyPDFLoader(path)
            documents.extend(loader.load())
        elif ext == '.txt':
            loader = TextLoader(path, encoding='utf-8')
            documents.extend(loader.load())
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.RAG_CHUNK_SIZE,
        chunk_overlap=settings.RAG_CHUNK_OVERLAP,
    )
    return splitter.split_documents(documents)
