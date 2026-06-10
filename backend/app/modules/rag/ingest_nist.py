"""Ingest the NIST AI RMF PDF into the RAG FAISS index.

The helper loads the local NIST AI RMF document, chunks it, annotates the
metadata, and merges the chunks into the existing vector store.
"""

import logging
import os
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS
from langchain_openai import OpenAIEmbeddings

logger = logging.getLogger(__name__)

# Path to the NIST AI RMF PDF
NIST_PDF_PATH = Path(__file__).parent.parent.parent.parent / (
    "data/regulatory_docs/NIST_AI_RMF_1.0.pdf"
)

# FAISS index path same as used by the existing RAG module
FAISS_INDEX_PATH = Path(__file__).parent.parent.parent.parent / (
    "data/faiss_index"
)

# Chunk settings keep consistent with existing ingestion
CHUNK_SIZE = 1000
CHUNK_OVERLAP = 200


def ingest_nist_ai_rmf() -> None:
    """Ingest NIST AI RMF 1.0 into the existing FAISS vector store."""
    if not NIST_PDF_PATH.exists():
        raise FileNotFoundError(
            f"NIST AI RMF PDF not found at {NIST_PDF_PATH}. "
            "Download it from: https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf"
        )

    # TODO: add support for NIST AI RMF 2.0 when published
    logger.info("Loading NIST AI RMF PDF from %s", NIST_PDF_PATH)
    loader = PyPDFLoader(str(NIST_PDF_PATH))
    pages = loader.load()
    logger.info("Loaded %d pages", len(pages))

    # Add framework metadata to every page before splitting
    for page in pages:
        page.metadata["framework"] = "NIST AI RMF 1.0"
        page.metadata["publisher"] = "NIST"
        page.metadata["year"] = "2023"

    # Split into chunks
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        separators=["\n\n", "\n", " ", ""],
    )
    chunks = splitter.split_documents(pages)
    logger.info("Split into %d chunks", len(chunks))

    # Ensure framework tag on every chunk (splitter can drop metadata)
    for chunk in chunks:
        if "framework" not in chunk.metadata:
            chunk.metadata["framework"] = "NIST AI RMF 1.0"

    # Load embeddings
    embeddings = OpenAIEmbeddings(
        openai_api_key=os.environ["OPENAI_API_KEY"]
    )

    # Load existing FAISS index and merge, or create new if none exists
    if FAISS_INDEX_PATH.exists():
        logger.info("Loading existing FAISS index from %s", FAISS_INDEX_PATH)
        vector_store = FAISS.load_local(
            str(FAISS_INDEX_PATH),
            embeddings,
            allow_dangerous_deserialization=True,
        )
        vector_store.add_documents(chunks)
        logger.info("Added NIST chunks to existing index")
    else:
        logger.info("No existing index found — creating new FAISS index")
        vector_store = FAISS.from_documents(chunks, embeddings)

    # Save updated index
    FAISS_INDEX_PATH.mkdir(parents=True, exist_ok=True)
    vector_store.save_local(str(FAISS_INDEX_PATH))
    logger.info(
        "FAISS index saved to %s with NIST AI RMF chunks", FAISS_INDEX_PATH
    )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingest_nist_ai_rmf()
