## Goal
- Fix 6 open-source issues across AegisAI (3 issues) and ai-code-reviewer (3 issues), creating separate branches and PRs from `main` for each, then fix CI failures on submitted PRs.

## Constraints & Preferences
- Each issue gets its own branch from `main`, committed and pushed independently
- Keep PRs limited to the scope of each issue
- Fork is `ionfwsrijan` for both repos; origin is upstream (`SdSarthak/AegisAI`, `kalyan-1845/ai-code-reviewer`)
- Do not merge with other branches or previous PRs
- All pushes go to the `ionfwsrijan` fork

## Progress
### Done
- AegisAI #919 — guard.py formatted webhook delivery in single-scan endpoint; added `deliver_webhook()` call to batch-scan endpoint (commit `58dedc5`). Branch: `fix/issue-919-guard-webhook-delivery`. Pushed to fork.
- AegisAI #920 — added `FAISS_INDEX_BASE_PATH` config; vector_store functions accept `user_id`; retrieval_chain and rag.py pass user context (commits `2f3f32b`, `625ffb0`, `f48710b`, `8920483`, `7f01eb9`). Branch: `fix/issue-920-faiss-tenant-isolation`. Pushed to fork.
- AegisAI #921 — replaced hardcoded analytics data with API calls; added `GET /analytics/system-risk` backend endpoint; rewritten `Analytics.tsx` with loading/error/empty states, skeletons, retry, system selector, dark/light theming (commit `981bb88`). Branch: `fix/issue-921-analytics-dashboard`. Pushed to fork.
- ai-code-reviewer #206 — restricted all 3 LLM prompt paths (analyze, chat, review-diff) to use RAG context only; forbids external knowledge, speculation, and fallback to training data (commit `61ebd65`). Branch: `fix/issue-206-rag-prompt-template`. Pushed to fork.
- ai-code-reviewer #224 — added client-side CSV export for audit findings; flattened fileReviews into rows with columns File/Category/Type/Line/Description/Suggestion; added `FileSpreadsheet` icon + Export CSV button (commit `54ff243`). Branch: `feature/issue-224-export-csv`. Pushed to fork.
- ai-code-reviewer #225 — redesigned pre-analysis empty-state dashboard with hero section, 4 feature cards (Security, Bugs, Performance, README), Quick Start numbered steps, polished sample repo buttons (commit `7c8f461`). Branch: `feature/issue-225-empty-state-ui`. Pushed to fork.

### In Progress
- Fixing CI failures on AegisAI PR #1027 (#920): Moved `os.makedirs` from `_get_index_path` to `create_vector_store` to prevent `os.path.exists` mock conflict in `test_rag_ingest.py` (commit `7f01eb9`)

### Blocked
- CI log requires GitHub authentication — cannot see exact error without sign-in

## Key Decisions
- Per-user FAISS isolation uses `{FAISS_INDEX_BASE_PATH}/user_{user_id}/` as index directory
- `rag_env` fixture in `test_rag_pipeline.py` must patch both `FAISS_INDEX_PATH` and `FAISS_INDEX_BASE_PATH`
- `decode_token()` used inline in `test_ingest_creates_faiss_index_on_disk` to derive user-scoped index path
- `os.makedirs` moved out of `_get_index_path` to prevent conflicts with `os.path.exists` mocking in tests
- `document_generator.py` `load_vector_store()` call (line 13) still uses no `user_id` — not yet fixed (not test code, not called in any test)
- CSV export is client-side (avoids backend changes)
- Empty-state uses a full-width structured dashboard rather than a simple centered message

## Next Steps
1. Push commit `7f01eb9` and verify PR #1027 CI passes
2. Verify PR #1025 (#921) CI passes after lint+changelog fix
3. Open all 6 PRs against upstream repos using the description templates
4. Fix `document_generator.py` to accept `user_id` parameter for full tenant isolation

## Critical Context
- PR #1027 (`fix/issue-920-faiss-tenant-isolation`) has 5 commits: `2f3f32b` (original), `625ffb0` (test mocks), `f48710b` (changelog), `8920483` (test_rag_pipeline fixture fix), `7f01eb9` (os.makedirs moved out of _get_index_path)
- Root cause of CI failure: `test_rag_ingest.py` patches `os.path.exists` globally (returning True), which made `os.makedirs` (called inside `_get_index_path`) skip parent directory creation, then the real `mkdir` system call failed in CI where parent dirs don't exist. Locally the tests passed because `faiss_data/` existed from a previous run.
- Pytest check (run id 27678743521/job 81860476067) previously failed with exit code 1
- Backend Tests (run id 27678743521/job 81860476812) previously failed with exit code 1
- Local test run with identical env vars passes: 419 passed, 1 skipped, 50 warnings
- `document_generator.py` line 13 calls `load_vector_store()` without `user_id` — this is a production bug for tenant isolation

## Relevant Files
- `AegisAI/backend/app/api/v1/guard.py`: #919 — webhook delivery fixes
- `AegisAI/backend/app/core/config.py`: #920 — `FAISS_INDEX_BASE_PATH`
- `AegisAI/backend/app/modules/rag/vector_store.py`: #920 — `_get_index_path()`, `create_vector_store(..., user_id=...)`, `load_vector_store(user_id=...)`, `check_index_exists(user_id=...)`
- `AegisAI/backend/app/modules/rag/retrieval_chain.py`: #920 — `get_qa_chain(user_id=...)`
- `AegisAI/backend/app/api/v1/rag.py`: #920 — ingest/query/stream pass `current_user.id`
- `AegisAI/backend/app/modules/llm/document_generator.py`: #920 — line 13 `load_vector_store()` missing `user_id` param
- `AegisAI/backend/app/api/v1/analytics.py`: #921 — added `GET /analytics/system-risk`
- `AegisAI/CHANGELOG.md`: #920, #921 entries added
- `AegisAI/backend/tests/test_rag_query.py`: #920 — mock updated to `lambda user_id=None`
- `AegisAI/backend/tests/integration/test_rag_feedback.py`: #920 — mock updated to `lambda user_id=None`
- `AegisAI/backend/tests/integration/test_rag_pipeline.py`: #920 — `rag_env` patched with `FAISS_INDEX_BASE_PATH`; test assertion uses `decode_token` to derive `user_index_dir`
- `AegisAI/backend/tests/test_retrieval_chain.py`: #920 — calls `load_vector_store()` without `user_id` (uses default `None`)
- `AegisAI/backend/tests/test_rag_ingest.py`: #920 — patches `app.api.v1.rag.create_vector_store` directly
- `AegisAI/CHANGELOG.md`: #920 entry
- `ai-code-reviewer/ai-engine/app.py`: #206 — system prompt restricted to RAG-only
- `ai-code-reviewer/frontend/src/App.tsx`: #224 (CSV export), #225 (empty-state UI)
