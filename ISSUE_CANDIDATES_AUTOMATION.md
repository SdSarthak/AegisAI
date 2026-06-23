# Issue Candidates

1. Title: fix : remove raw user_prompt from LLMGuard.guard() result dict
   Type: fix
   Category: bug
   Files: backend/app/modules/guard/llm_guard.py
   Summary: LLMGuard.guard() includes the raw user_prompt in plaintext in the result dict (line 98), contradicting the hash-only storage design documented in guard_scan_log.py. The raw prompt leaks through API responses and logs.
   Verification: cd backend && pytest tests/test_guard.py tests/test_guard_api.py -v -q
   Conflict risk: low

2. Title: fix : add count field to DailyBucket Pydantic schema in guard_stats
   Type: fix
   Category: bug
   Files: backend/app/schemas/guard_stats.py, backend/app/api/v1/guard.py
   Summary: GET /guard/stats recomputes a count field for each daily bucket (lines 871-876 of guard.py) but DailyBucket schema has no count field, so Pydantic silently strips it from the response.
   Verification: cd backend && pytest tests/test_guard_stats.py -v -q
   Conflict risk: low

3. Title: fix : add user_id parameter to _index_size_bytes for correct FAISS path
   Type: fix
   Category: bug
   Files: backend/app/api/v1/rag.py
   Summary: _index_size_bytes() always reads from settings.FAISS_INDEX_PATH (global), but create_vector_store() saves to user-scoped path when user_id is set, causing index_size_bytes to always report 0 or wrong size for authenticated users.
   Verification: cd backend && pytest tests/test_rag.py tests/integration/test_rag_pipeline.py -v -q
   Conflict risk: low

4. Title: fix : move registration rate-limit record out of finally block in auth.py
   Type: fix
   Category: bug
   Files: backend/app/api/v1/auth.py
   Summary: POST /register records rate-limit attempts in a finally block, meaning successful registrations consume the rate-limit budget. After 3 successful registrations, the 4th is incorrectly 429'd. Login correctly records only on failure.
   Verification: cd backend && pytest tests/test_auth.py -v -q
   Conflict risk: low

5. Title: fix : replace datetime.utcnow() with datetime.now(timezone.utc) in guard.py
   Type: fix
   Category: bug
   Files: backend/app/api/v1/guard.py
   Summary: GuardScanLog.scanned_at uses naive datetime.utcnow() (lines 161, 766) but cursor pagination makes datetimes timezone-aware (lines 492-510). On PostgreSQL this causes 'cannot compare timestamp without time zone with timestamp with time zone'. Fix by replacing utcnow() with now(timezone.utc).
   Verification: cd backend && pytest tests/test_guard_api.py tests/test_guard_stats.py -v -q
   Conflict risk: low
