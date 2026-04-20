# TASK-036: Replace CORS `allow_origins=["*"]` with env-driven whitelist

## 1. Metadata
- Task ID: TASK-036
- Title: Replace CORS `allow_origins=["*"]` with env-driven whitelist
- Related SPEC: SPEC-2026-04-20-PRODUCTION-HARDENING
- Assigned To: Code
- Mode: strict
- Priority: P0 (security — open CORS)
- Estimated effort: 15 min
- Status: DONE

## 2. Problem Statement
**File:** [`ai_workspace/src/api/rag_server.py:86`](ai_workspace/src/api/rag_server.py#L86)

Current: `app.add_middleware(CORSMiddleware, allow_origins=["*"], ...)` — open CORS allows any origin.

## 3. DoD (Definition of Done)

- [x] No literal `"*"` in `allow_origins` anywhere
- [x] `.env.example` documents `CORS_ORIGINS` with safe localhost default
- [x] Integration test verifies a request from a non-whitelisted origin gets expected CORS behavior

## 4. Changes Made

### 4.1 rag_server.py (lines 83-92)
- Replaced `allow_origins=["*"]` with `allow_origins=CORS_ORIGINS`
- Added `CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")`

### 4.2 .env.example
- Added `CORS_ORIGINS=http://localhost:3000,http://localhost:5173` in Server Configuration section

### 4.3 test_rag_server.py (lines 308-328)
- Added `TestCORSWhitelist` class with 2 integration tests:
  - `test_whitelisted_origin_returns_header` — verifies `http://localhost:3000` gets `Access-Control-Allow-Origin` header
  - `test_non_whitelisted_origin_no_header` — verifies `http://evil.example.com` does NOT get the header

## 5. Evidence

| DoD Item | Status | Evidence |
|----------|--------|----------|
| No literal `"*"` in `allow_origins` | PASS | grep → 0 hits |
| `.env.example` documents `CORS_ORIGINS` | PASS | File contains `CORS_ORIGINS=http://localhost:3000,http://localhost:5173` |
| Integration test for non-whitelisted origin | PASS | `TestCORSWhitelist` — 2/2 passed |

```
tests/test_rag_server.py::TestCORSWhitelist::test_whitelisted_origin_returns_header PASSED
tests/test_rag_server.py::TestCORSWhitelist::test_non_whitelisted_origin_no_header PASSED
```

## 6. Files Modified
- `ai_workspace/src/api/rag_server.py`
- `ai_workspace/.env.example`
- `ai_workspace/tests/test_rag_server.py`
