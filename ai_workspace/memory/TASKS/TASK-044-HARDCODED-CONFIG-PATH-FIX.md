# TASK-044: Fix Hardcoded Config Path in health_check.py

- **Task ID**: TASK-044
- **Title**: Fix Hardcoded Config Path in health_check.py
- **Status**: DONE
- **Assigned To**: Code
- **Mode**: strict
- **Created**: 2026-04-21
- **Priority**: P1 High
- **Parent Issue**: Health check reports neo4j and llama_cpp as unhealthy due to `[Errno 2] No such file or directory: './ai_workspace/config/default.yaml'`

## Problem Statement

The health check endpoint (`/health`) reports two components as unhealthy:
- **neo4j**: `[Errno 2] No such file or directory: './ai_workspace/config/default.yaml'`
- **llama_cpp**: `[Errno 2] No such file or directory: './ai_workspace/config/default.yaml'`

Root cause: [`health_check.py`](ai_workspace/src/api/health_check.py:82) and [`health_check.py`](ai_workspace/src/api/health_check.py:130) use a hardcoded relative path `"./ai_workspace/config/default.yaml"` which is incorrect.

The server is started from the project root `/home/tarik/Sandbox/my-plugin/rag-project/`, where the config file is located at `ai_workspace/config/default.yaml`. The relative path `"./ai_workspace/config/default.yaml"` would only work if the server was started from a parent directory.

## Acceptance Criteria

1. Config path in `check_neo4j()` resolves correctly from any working directory
2. Config path in `check_llama_cpp()` resolves correctly from any working directory
3. Both neo4j and llama_cpp health checks no longer throw `[Errno 2]`
4. If config file doesn't exist, health check degrades gracefully (returns UNKNOWN or a sensible default)
5. All existing tests pass

## DoD (Definition of Done)

- [x] 1. Config path uses `Path(__file__).resolve().parent.parent.parent / "config" / "default.yaml"` — verified at line 50
- [x] 2. Both `check_neo4j()` and `check_llama_cpp()` use `self._config_path` — verified at lines 87, 138
- [x] 3. Graceful fallback when config file is missing (use env vars or defaults) — `if self._config_path.exists()` check added in both methods
- [x] 4. No hardcoded `"./ai_workspace/config/default.yaml"` remains in health_check.py — `grep` returns 0 hits
- [x] 5. All existing tests pass (`pytest ai_workspace/tests/test_health_check.py -v`) — 24 passed
- [x] 6. Health check endpoint returns valid JSON for neo4j and llama_cpp (no 500 errors) — verified: neo4j=`unknown` (graceful), llama_cpp=`healthy`
- [ ] 7. Reviewer approval (PASS or PASS_WITH_NOTES on REVIEW_REPORT)

## Implementation Plan

1. In `HealthChecker.__init__()`, compute the config path once using `Path(__file__).resolve()` to get the project root
2. Replace hardcoded `"./ai_workspace/config/default.yaml"` in `check_neo4j()` with the computed path
3. Replace hardcoded `"./ai_workspace/config/default.yaml"` in `check_llama_cpp()` with the computed path
4. Add graceful fallback: if config file doesn't exist, use env vars (`NEO4J_URI`, `LLM_ENDPOINT`) or hardcoded defaults
5. Run tests and verify

## Evidence Requirements

- `grep -r '"./ai_workspace/config/default.yaml"' ai_workspace/src/api/health_check.py` → 0 hits
- `pytest ai_workspace/tests/test_health_check.py -v` → all pass
- `curl http://localhost:8000/health` → neo4j and llama_cpp return valid status (not `[Errno 2]`)

## Decision and Rationale

- **Config path resolution**: Use `Path(__file__).resolve().parent.parent.parent` to traverse from `src/api/health_check.py` → `src/` → `ai_workspace/` → project root, then append `config/default.yaml`. This is robust regardless of CWD.
- **Graceful degradation**: If config file is missing, fall back to env vars or sensible defaults. This avoids breaking health checks in environments where config is managed externally.

## Notes

- The `default.yaml` file exists at `ai_workspace/config/default.yaml` and contains `llm` and `server` sections but no `neo4j` section. The `check_neo4j()` method should handle missing neo4j config gracefully.
- Related: TASK-042 (hardcoded ports), TASK-043 (hardcoded Neo4j port) — this task is about config file path resolution, not ports.
