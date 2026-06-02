# Regulatory Documents

This directory is the intended home for regulatory PDFs used by the RAG
Intelligence module.  The actual documents are **downloaded at setup time**
by the bootstrap script rather than committed to version control.

## Quick Start

```bash
cd backend
python -m scripts.seed_regulatory_docs
```

The script will:
1. Download public regulatory PDFs to a temp directory
2. Chunk and embed each document into the FAISS vector index
3. Register metadata in the `ingested_documents` database table
4. Skip any document that has already been ingested (SHA-256 dedup)

## Included Documents

### 1. EU AI Act (Regulation EU 2024/1689)

- File: `eu_ai_act.pdf`
- Source:
  https://eur-lex.europa.eu/legal-content/EN/TXT/?uri=CELEX:32024R1689
- Retrieved on: 2026-05-12

### 2. GDPR (Regulation EU 2016/679)

- File: `gdpr_regulation_eu_2016_679.pdf`
- Source:
  https://eur-lex.europa.eu/eli/reg/2016/679/oj/eng
- Retrieved on: 2026-05-12

### 3. NIST AI RMF 1.0

- File: `nist_ai_rmf_1_0.pdf`
- Source:
  https://www.nist.gov/itl/ai-risk-management-framework
- Retrieved on: 2026-05-12

### 4. ISO/IEC 42001:2023 Overview

- File: `iso_42001_overview.txt` (generated summary)
- Sources:
  https://www.iso.org/standard/81230.html
  https://learn.microsoft.com/en-us/compliance/regulatory/offering-iso-42001
- Retrieved on: 2026-05-12

### 4. India Digital Personal Data Protection (DPDP) Act 2023

- File: `dpdp_act_2023.pdf`
- Source:
  https://www.meity.gov.in/data-protection-framework
- Retrieved on: 2026-05-28

## Notes

- GDPR and NIST AI RMF documents were obtained from official public sources.
- ISO/IEC 42001 full standard text is not redistributed due to copyright
  restrictions. Only a publicly accessible overview is included.
- The bootstrap script is idempotent — safe to run multiple times.