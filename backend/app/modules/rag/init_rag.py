import logging
import os
import urllib.request
from pathlib import Path
import threading

from langchain.text_splitter import RecursiveCharacterTextSplitter
from app.modules.rag.document_loader import load_documents_from_paths
from app.modules.rag.vector_store import create_vector_store, check_index_exists

logger = logging.getLogger(__name__)

REGULATORY_DOCS_DIR = Path(__file__).parent.parent.parent.parent / "data" / "regulatory_docs"

DOCUMENTS_TO_FETCH = {
    "eu_ai_act.pdf": "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32024R1689",
    "gdpr.pdf": "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/?uri=CELEX:32016R0679",
    "nist_ai_rmf.pdf": "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf",
}

ISO_42001_OVERVIEW_TEXT = """
ISO/IEC 42001:2023 - Information Technology - Artificial Intelligence - Management System
Overview:
ISO/IEC 42001 is a global standard that specifies requirements for establishing, implementing, 
maintaining, and continually improving an Artificial Intelligence Management System (AIMS).
It is designed for organizations providing or utilizing AI-based products or services, ensuring 
responsible development and use of AI systems. 

Key Requirements:
1. Context of the organization: Understanding the organization and its context regarding AI.
2. Leadership: Commitment from top management, establishing an AI policy.
3. Planning: Actions to address risks and opportunities, including AI risk assessment and treatment.
4. Support: Providing necessary resources, competence, awareness, and documented information.
5. Operation: Operational planning and control, conducting AI risk assessments.
6. Performance Evaluation: Monitoring, measurement, analysis, internal audit, and management review.
7. Improvement: Continual improvement and managing nonconformities.

It emphasizes principles such as transparency, explainability, fairness, and accountability.
"""

def download_file(url: str, dest_path: Path):
    """Download a file from a URL to a local destination."""
    logger.info(f"Downloading {url} to {dest_path}")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req) as response:
        with open(dest_path, "wb") as f:
            f.write(response.read())
    if dest_path.stat().st_size == 0:
        dest_path.unlink()
        raise ValueError("Downloaded file is empty (possibly blocked by WAF).")

def initialize_rag_store():
    """Fetch documents and ingest them into the FAISS vector store if the index does not exist."""
    if check_index_exists():
        logger.info("FAISS index already exists. Skipping RAG pre-load.")
        return

    logger.info("FAISS index not found. Initiating regulatory document pre-load...")
    
    REGULATORY_DOCS_DIR.mkdir(parents=True, exist_ok=True)
    
    saved_paths = []
    
    # 1. Download PDFs
    for filename, url in DOCUMENTS_TO_FETCH.items():
        dest_path = REGULATORY_DOCS_DIR / filename
        if not dest_path.exists():
            try:
                download_file(url, dest_path)
            except Exception as e:
                logger.error(f"Failed to download {filename} from {url}: {e}")
                continue
        else:
            logger.info(f"File {filename} already exists at {dest_path}")
        saved_paths.append(str(dest_path))
        
    # 2. Generate ISO 42001 overview
    iso_path = REGULATORY_DOCS_DIR / "iso_42001_overview.txt"
    if not iso_path.exists():
        logger.info(f"Generating {iso_path}")
        with open(iso_path, "w", encoding="utf-8") as f:
            f.write(ISO_42001_OVERVIEW_TEXT)
    saved_paths.append(str(iso_path))
    
    # Check if there are also existing PDFs in the directory that we should include
    for file in REGULATORY_DOCS_DIR.iterdir():
        if file.suffix.lower() == '.pdf' and str(file) not in saved_paths:
            saved_paths.append(str(file))

    if not saved_paths:
        logger.warning("No documents available to ingest.")
        return

    # 3. Process and Chunk Documents
    logger.info("Loading documents for FAISS ingestion...")
    try:
        raw_chunks = load_documents_from_paths(saved_paths)
        
        # Filter empty chunks
        chunks = [
            chunk for chunk in raw_chunks 
            if chunk.page_content and chunk.page_content.strip()
        ]
        
        if not chunks:
            logger.warning("Could not extract valid text from downloaded documents.")
            return

        # Use the same chunk settings as existing ingest routes
        splitter = RecursiveCharacterTextSplitter(
            chunk_size=1000,
            chunk_overlap=200,
            separators=["\n\n", "\n", " ", ""],
        )
        split_chunks = splitter.split_documents(chunks)

        # 4. Build FAISS Index
        logger.info(f"Building FAISS index from {len(split_chunks)} chunks...")
        create_vector_store(split_chunks)
        logger.info("RAG pre-load complete. FAISS index created successfully.")
        
    except Exception as e:
        logger.error(f"Failed to build FAISS index during pre-load: {e}")

def run_rag_initialization_in_background():
    """Start the initialization in a daemon thread so it doesn't block FastAPI startup."""
    thread = threading.Thread(target=initialize_rag_store, daemon=True)
    thread.start()
