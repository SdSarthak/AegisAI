#!/usr/bin/env python
"""Seed the FAISS knowledge base with publicly available regulatory PDFs.

Usage::

    cd backend
    python -m scripts.seed_regulatory_docs

The script downloads official regulatory documents from public government
sources, chunks them, embeds them, and merges them into the local FAISS
index.  Metadata rows are persisted in the ``ingested_documents`` table
so the dashboard can display what has been loaded.

Documents loaded:
    1. EU AI Act  (Regulation EU 2024/1689) — from EUR-Lex
    2. GDPR       (Regulation EU 2016/679)  — from EUR-Lex
    3. NIST AI RMF 1.0                      — from NIST.gov
    4. ISO/IEC 42001:2023 Overview          — generated summary text
"""

import hashlib
import os
import sys
import tempfile
from pathlib import Path

# Ensure ``backend/`` is on sys.path when invoked via ``python -m``.
_backend_dir = Path(__file__).resolve().parent.parent
if str(_backend_dir) not in sys.path:
    sys.path.insert(0, str(_backend_dir))

# Set required env vars *before* importing app modules.
os.environ.setdefault("DATABASE_URL", "sqlite:///./aegis_dev.db")
os.environ.setdefault("SECRET_KEY", "seed-script-secret-key")

from sqlalchemy.orm import Session  # noqa: E402

from app.core.database import SessionLocal, Base, engine  # noqa: E402
from app.models.ingested_document import IngestedDocument, SourceType  # noqa: E402
from app.modules.rag.document_loader import load_documents_from_paths  # noqa: E402
from app.modules.rag.vector_store import merge_into_vector_store  # noqa: E402

# ---------------------------------------------------------------------------
# Registry of publicly downloadable regulatory documents
# ---------------------------------------------------------------------------

REGULATORY_DOCS = [
    {
        "name": "EU AI Act",
        "filename": "eu_ai_act.pdf",
        "url": (
            "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/"
            "?uri=OJ:L_202401689"
        ),
    },
    {
        "name": "GDPR",
        "filename": "gdpr_regulation_eu_2016_679.pdf",
        "url": (
            "https://eur-lex.europa.eu/legal-content/EN/TXT/PDF/"
            "?uri=CELEX:32016R0679"
        ),
    },
    {
        "name": "NIST AI RMF 1.0",
        "filename": "nist_ai_rmf_1_0.pdf",
        "url": (
            "https://nvlpubs.nist.gov/nistpubs/ai/NIST.AI.100-1.pdf"
        ),
    },
]

# ISO 42001 full text is copyrighted — we generate a summary text file
# from publicly available information instead.
ISO_42001_OVERVIEW = """\
ISO/IEC 42001:2023 — Artificial Intelligence Management System (AIMS)

Overview
--------
ISO/IEC 42001 is the world's first international management system standard
for Artificial Intelligence.  Published in December 2023, it provides a
structured framework for organizations to manage AI-related risks and
opportunities throughout the AI lifecycle.

Scope (Clause 1)
----------------
The standard specifies requirements for establishing, implementing,
maintaining, and continually improving an AI Management System (AIMS)
within organizations that develop, provide, or use AI-based products
or services.

Key Clauses
-----------
Clause 4 — Context of the organization: Determine internal/external issues
and interested parties relevant to the AIMS.

Clause 5 — Leadership: Top management commitment, AI policy, roles and
responsibilities.

Clause 6 — Planning: Address risks and opportunities, set AI objectives,
plan changes.

Clause 7 — Support: Resources, competence, awareness, communication,
documented information.

Clause 8 — Operation: Operational planning, AI risk assessment, AI risk
treatment, AI system impact assessment.

Clause 9 — Performance evaluation: Monitoring, measurement, analysis,
internal audit, management review.

Clause 10 — Improvement: Nonconformity, corrective action, continual
improvement.

Annex A — Reference control objectives and controls
Annex B — Implementation guidance for AI controls
Annex C — Potential AI-related sources of risk
Annex D — Use of the AI management system across domains

Certification
-------------
Organizations can be certified to ISO/IEC 42001 by accredited certification
bodies.  Microsoft Azure, for example, has achieved ISO 42001 certification
for its AI services.

Relationship to Other Standards
-------------------------------
- ISO/IEC 23894 (AI Risk Management)
- ISO/IEC 38507 (Governance of AI)
- ISO/IEC 22989 (AI Concepts and Terminology)
- EU AI Act (Regulation EU 2024/1689)
- NIST AI RMF 1.0

References
----------
- https://www.iso.org/standard/81230.html
- https://learn.microsoft.com/en-us/compliance/regulatory/offering-iso-42001
"""


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _sha256_file(path: str) -> str:
    """Return the SHA-256 hex digest of a local file."""
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for block in iter(lambda: f.read(1 << 16), b""):
            h.update(block)
    return h.hexdigest()


def _download(url: str, dest: str) -> None:
    """Download *url* to *dest* using ``urllib`` (no extra deps)."""
    import urllib.request
    import ssl

    # Some government sites use strict TLS; default context is fine.
    ctx = ssl.create_default_context()
    req = urllib.request.Request(url, headers={"User-Agent": "AegisAI-Seeder/1.0"})
    with urllib.request.urlopen(req, context=ctx, timeout=120) as resp, \
            open(dest, "wb") as out:
        while True:
            chunk = resp.read(1 << 16)
            if not chunk:
                break
            out.write(chunk)


def _already_ingested(db: Session, file_hash: str) -> bool:
    """Return True if a document with this hash is already in the registry."""
    return (
        db.query(IngestedDocument)
        .filter(IngestedDocument.file_hash == file_hash)
        .first()
        is not None
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def seed_regulatory_docs() -> None:
    """Download, chunk, embed, and register all regulatory documents."""
    # Ensure DB tables exist.
    Base.metadata.create_all(bind=engine)
    db: Session = SessionLocal()

    tmp_dir = tempfile.mkdtemp(prefix="aegis_seed_")
    total_ingested = 0

    try:
        # ── 1. Downloadable PDFs ──────────────────────────────────────────
        for doc_info in REGULATORY_DOCS:
            name = doc_info["name"]
            filename = doc_info["filename"]
            url = doc_info["url"]
            dest = os.path.join(tmp_dir, filename)

            print(f"\n{'='*60}")
            print(f"Processing: {name}")
            print(f"{'='*60}")

            print(f"  Downloading from {url} ...")
            try:
                _download(url, dest)
            except Exception as exc:
                print(f"  ⚠ Download failed: {exc}")
                print(f"  Skipping {name}.")
                continue

            file_hash = _sha256_file(dest)
            if _already_ingested(db, file_hash):
                print(f"  ✓ Already ingested (hash: {file_hash[:12]}…). Skipping.")
                continue

            file_size = os.path.getsize(dest)
            print(f"  File size: {file_size:,} bytes")

            print("  Chunking & embedding ...")
            try:
                chunks = load_documents_from_paths([dest])
                merge_into_vector_store([dest])
            except Exception as exc:
                print(f"  ⚠ Ingestion failed: {exc}")
                print(f"  Skipping {name}.")
                continue

            record = IngestedDocument(
                filename=filename,
                source_type=SourceType.PRE_LOADED,
                regulation_name=name,
                file_hash=file_hash,
                file_size_bytes=file_size,
                chunk_count=len(chunks),
                uploaded_by_id=None,
            )
            db.add(record)
            db.commit()
            print(f"  ✓ Ingested {len(chunks)} chunks.")
            total_ingested += 1

        # ── 2. ISO 42001 overview (text, not PDF) ────────────────────────
        print(f"\n{'='*60}")
        print("Processing: ISO/IEC 42001 Overview")
        print(f"{'='*60}")

        iso_path = os.path.join(tmp_dir, "iso_42001_overview.txt")
        with open(iso_path, "w", encoding="utf-8") as f:
            f.write(ISO_42001_OVERVIEW)

        file_hash = _sha256_file(iso_path)
        if _already_ingested(db, file_hash):
            print("  ✓ Already ingested. Skipping.")
        else:
            # The text splitter in document_loader uses PyPDFLoader which
            # expects PDFs.  For plain text we do a minimal chunking here.
            from langchain.text_splitter import RecursiveCharacterTextSplitter
            from langchain.schema import Document as LCDocument
            from app.core.config import settings as cfg

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=cfg.RAG_CHUNK_SIZE,
                chunk_overlap=cfg.RAG_CHUNK_OVERLAP,
            )
            raw_doc = LCDocument(
                page_content=ISO_42001_OVERVIEW,
                metadata={"source": "iso_42001_overview.txt"},
            )
            chunks = splitter.split_documents([raw_doc])

            # Embed and merge
            from langchain_community.vectorstores import FAISS
            from app.modules.rag.vector_store import get_embeddings

            embeddings = get_embeddings()
            new_store = FAISS.from_documents(chunks, embeddings)

            index_path = cfg.FAISS_INDEX_PATH
            if os.path.exists(index_path):
                existing = FAISS.load_local(
                    index_path, embeddings,
                    allow_dangerous_deserialization=True,
                )
                existing.merge_from(new_store)
                existing.save_local(index_path)
            else:
                new_store.save_local(index_path)

            record = IngestedDocument(
                filename="iso_42001_overview.txt",
                source_type=SourceType.PRE_LOADED,
                regulation_name="ISO/IEC 42001",
                file_hash=file_hash,
                file_size_bytes=os.path.getsize(iso_path),
                chunk_count=len(chunks),
                uploaded_by_id=None,
            )
            db.add(record)
            db.commit()
            print(f"  ✓ Ingested {len(chunks)} chunks.")
            total_ingested += 1

        # ── Summary ──────────────────────────────────────────────────────
        print(f"\n{'='*60}")
        print(f"Done!  {total_ingested} document(s) ingested.")
        all_docs = db.query(IngestedDocument).all()
        print(f"Total documents in registry: {len(all_docs)}")
        for d in all_docs:
            print(f"  • {d.filename}  ({d.chunk_count} chunks, {d.source_type.value})")
        print(f"{'='*60}")

    finally:
        import shutil
        shutil.rmtree(tmp_dir, ignore_errors=True)
        db.close()


if __name__ == "__main__":
    seed_regulatory_docs()
