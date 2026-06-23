"""
NIST AI RMF 1.0 document ingestion into the AegisAI FAISS vector store.

Loads the NIST AI RMF PDF, splits it into chunks, embeds them with
framework metadata tagging, and adds them to the existing FAISS index
alongside EU AI Act, GDPR, and ISO 42001 documents.

Run once:
    python -m app.modules.rag.ingest_nist
"""

from __future__ import annotations

import logging
from pathlib import Path

from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.vectorstores import FAISS

from app.core.config import settings
from app.modules.rag.embeddings import get_embeddings

logger = logging.getLogger(__name__)

# Path to the NIST AI RMF PDF
NIST_PDF_PATH = Path(__file__).parent.parent.parent.parent / (
    "data/regulatory_docs/NIST_AI_RMF_1.0.pdf"
)

# FAISS index path from settings
FAISS_INDEX_PATH = Path(settings.FAISS_INDEX_PATH)

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

    # Load embeddings using the shared factory
    try:
        embeddings = get_embeddings()
    except Exception as exc:
        raise RuntimeError(
            f"Failed to initialise embeddings: {exc}"
        ) from exc

    # Load existing FAISS index and merge, or create new if none exists
    try:
        if FAISS_INDEX_PATH.exists():
            logger.info("Loading existing FAISS index from %s", FAISS_INDEX_PATH)
            vector_store = FAISS.load_local(
                str(FAISS_INDEX_PATH),
                embeddings,
                allow_dangerous_deserialization=False,
            )
            vector_store.add_documents(chunks)
            logger.info("Added NIST chunks to existing index")
        else:
            logger.info("No existing index found — creating new FAISS index")
            vector_store = FAISS.from_documents(chunks, embeddings)
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Failed to build or merge FAISS index: {exc}. "
            "Ensure the FAISS index path is accessible and not corrupted."
        ) from exc

    # Save updated index
    try:
        FAISS_INDEX_PATH.mkdir(parents=True, exist_ok=True)
        vector_store.save_local(str(FAISS_INDEX_PATH))
        logger.info(
            "FAISS index saved to %s with NIST AI RMF chunks", FAISS_INDEX_PATH
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(
            f"Failed to save FAISS index to {FAISS_INDEX_PATH}: {exc}. "
            "Check write permissions and disk space."
        ) from exc


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    ingest_nist_ai_rmf()