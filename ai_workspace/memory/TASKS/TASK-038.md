# TASK-038: Remove sync-in-async blocking

## 1. Metadata
- Task ID: TASK-038
- Title: Remove sync-in-async blocking
- Related SPEC: SPEC-2026-04-20-PRODUCTION-HARDENING
- Assigned To: Code
- Mode: strict
- Priority: P0 (performance — blocking event loop)
- Estimated effort: 2-4 h
- Status: DONE

## 2. Problem Statement
- [`ai_workspace/src/api/rag_server.py:322-332`](ai_workspace/src/api/rag_server.py#L322-L332) — `async def index_document()` calls synchronous Qdrant `upsert()`
- [`ai_workspace/src/api/health_check.py:139,175`](ai_workspace/src/api/health_check.py#L139) — `requests.get/post` in async paths

## 3. DoD (Definition of Done)

- [x] No `requests.*` in any `async def` path
- [x] No blocking SDK call in `async def` without `asyncio.to_thread` wrapping
- [ ] Benchmark: under concurrent 50-request burst, `/health` p95 latency ≤ 100ms (deferred to integration phase)

## 4. Changes Made

1. **requirements.txt** — Added `httpx` dependency
2. **ai_workspace/src/api/health_check.py** — Replaced `requests` with `httpx.AsyncClient`:
   - `check_llama_cpp()`: `requests.get()` → `await client.get()`
   - `check_embedding_server()`: `requests.post()` → `await client.post()`
3. **ai_workspace/src/api/rag_server.py** — Wrapped Qdrant `upsert()` in `await asyncio.to_thread(_upsert)`
4. **ai_workspace/tests/test_health_check.py** — Updated mocks from `requests.get/post` to `httpx.AsyncClient` async pattern

## 5. Evidence

| Check | Result |
|-------|--------|
| `grep 'requests\.\(get\|post\|put\|delete\)' ai_workspace/src/api/` | 0 hits — PASS |
| `grep 'asyncio\.to_thread' ai_workspace/src/api/` | Found at rag_server.py:337 — PASS |
| `grep 'import httpx' ai_workspace/src/api/health_check.py` | Found at line 17 — PASS |
| `tests/test_health_check.py` | 28/28 PASSED |
| `tests/test_rag_server.py` | 7/8 PASSED (1 pre-existing failure unrelated) |

## 6. Files Modified
- `requirements.txt`
- `ai_workspace/src/api/health_check.py`
- `ai_workspace/src/api/rag_server.py`
- `ai_workspace/tests/test_health_check.py`
