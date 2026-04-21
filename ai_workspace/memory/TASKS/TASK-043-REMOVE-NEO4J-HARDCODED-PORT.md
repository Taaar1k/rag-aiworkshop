# TASK-043: Remove Hardcoded Neo4j Port (7687) from src/

**Status:** DONE
**Type:** Refactor
**Priority:** Medium
**Execution Mode:** Light
**Assigned To:** Code Agent → Reviewer Agent
**Created:** 2026-04-21
**Completed:** 2026-04-21
**Reviewed By:** PM Agent (Pre-merge Gate)
**Review Date:** 2026-04-21
**Review Result:** PASS

---

## Description

TASK-042 replaced all LLM/Embedding/RAG server hardcoded ports, but missed 2 Neo4j port 7687 references in `src/`. These should use `os.getenv("NEO4J_URI", "bolt://localhost:7687")` instead of hardcoded defaults.

`.env.example` already documents `NEO4J_URI` (line 87, commented out).

---

## Findings

### 1. `ai_workspace/src/graph/graph_retriever.py` (line 25)

**Current:**
```python
neo4j_uri: str = "bolt://localhost:7687"
```

**Required:**
```python
neo4j_uri: str = os.getenv("NEO4J_URI", "bolt://localhost:7687")
```

### 2. `ai_workspace/src/api/health_check.py` (line ~200, Neo4j health check)

**Current:**
```python
uri = neo4j_config.get("uri", "bolt://localhost:7687")
```

**Required:**
```python
uri = neo4j_config.get("uri", os.getenv("NEO4J_URI", "bolt://localhost:7687"))
```

---

## Files NOT to Modify

- `ai_workspace/.env.example` — already has `NEO4J_URI` documented (line 87)
- `ai_workspace/tests/` — test files with hardcoded ports are acceptable for mock configs
- `ai_workspace/test_complete_system.py` — test script, not production code

---

## Acceptance Criteria

1. Zero hardcoded `bolt://localhost:7687` in `src/` production code — all use `os.getenv("NEO4J_URI", ...)`
2. Default value preserved for backward compatibility
3. `.env.example` already documents `NEO4J_URI` — no changes needed
4. All existing tests pass after changes

---

## DoD (Definition of Done)

- [x] All hardcoded Neo4j ports replaced with `os.getenv("NEO4J_URI", ...)` in `src/` files
  - Evidence: `src/graph/graph_retriever.py` line 25 uses `os.getenv()`. `src/api/health_check.py` line 98 uses `os.getenv()`. Verified via `rg "bolt://localhost:7687" --type py ai_workspace/src/` — only `os.getenv` matches found.
- [x] Default value preserved (`bolt://localhost:7687`)
- [x] All tests pass (`pytest ai_workspace/tests/ -v --tb=short`) — 377 passed (pre-existing 9 failed + 5 errors unrelated to this task)
- [x] Self-audit: `rg "bolt://localhost:7687" --type py ai_workspace/src/` returns only `os.getenv` matches
- [x] Reviewer approval (PASS or PASS_WITH_NOTES on REVIEW_REPORT) — PASS on TASK-043-REVIEW_REPORT.md

---

## Implementation Notes

- `os` is already imported in both files
- Neo4j is optional (guarded by `NEO4J_AVAILABLE` flag in `graph_retriever.py`)
- The default should remain `bolt://localhost:7687` for local development
