# Issue Candidates

1. Title: fix : validate RAG PDF inputs to return 400 on malformed payloads
   Type: fix
   Category: bug
   Files: backend/app/api/v1/rag.py
   Summary: The RAG document ingestion endpoint does not validate that uploaded PDF files are actually valid PDF byte streams before passing them to the document loader. Malformed or truncated PDFs cause unhandled exceptions resulting in 500 responses instead of returning a 400 Bad Request with a descriptive error.
   Verification: cd backend && python3 -m pytest tests/test_rag_ingest.py -v --no-header
   Conflict risk: low

2. Title: fix : replace datetime.utcnow() with datetime.now(timezone.utc) in GuardScanLog
   Type: fix
   Category: bug
   Files: backend/app/models/guard_scan_log.py
   Summary: GuardScanLog.scanned_at and created_at use the deprecated datetime.utcnow() which returns a naive datetime. On PostgreSQL this causes "naive datetime cannot be used with PyGreSQL/psycopg2" errors in cursor-based pagination. Replace with datetime.now(timezone.utc).
   Verification: cd backend && python3 -m pytest tests/ -v --no-header -k guard
   Conflict risk: low

3. Title: fix : move registration rate-limit record out of finally block in auth.py
   Type: fix
   Category: bug
   Files: backend/app/api/v1/auth.py
   Summary: The register() function's finally block calls _record_attempt() unconditionally — this records successful registrations as rate-limit events, diluting the rate limit counter. Move the _record_attempt call into the HTTPException handler and the generic Exception handler so only failed attempts are counted.
   Verification: cd backend && python3 -m pytest tests/test_auth.py -v --no-header
   Conflict risk: low

4. Title: test : add unit tests for explainer engine keyword matching
   Type: test
   Category: test
   Files: backend/tests/test_explainer_engine.py, backend/app/modules/explainer/engine.py
   Summary: backend/app/modules/explainer/engine.py has no test coverage. Add unit tests for the classify_risk_level and _build_response helper functions, covering keyword matching for all FACTOR_KEYWORDS entries and EU AI Act article reference resolution.
   Verification: cd backend && python3 -m pytest tests/test_explainer_engine.py -v --no-header
   Conflict risk: low

5. Title: test : add unit tests for CursorPaginatedResponse schema
   Type: test
   Category: test
   Files: backend/tests/test_schemas.py
   Summary: backend/app/schemas/pagination.py defines CursorPaginatedResponse but it has no tests. test_schemas.py only covers PaginatedResponse. Add tests for CursorPaginatedResponse: required fields (items, limit, next_cursor), optional next_cursor=None, serialization round-trip, and generic type handling.
   Verification: cd backend && python3 -m pytest tests/test_schemas.py -v --no-header
   Conflict risk: low
