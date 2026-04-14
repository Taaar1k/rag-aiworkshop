# TASK-019 v2: Mark remaining llama.cpp-dependent test as integration

## 1. Metadata
- Task ID: TASK-019-v2
- Created: 2026-04-17
- Assigned to: Code
- Mode: light
- Status: DONE (already applied — decorator present at line 79)
- Priority: P1

## 2. Context
After TASK-019 v1 marked 3 tests as `@pytest.mark.integration`, a 4th llama-dependent test still fails in the default `pytest tests/` run:

```
FAILED tests/test_rag_server.py::TestChatCompletions::test_chat_completions_returns_correct_format
E   AssertionError: assert 'id' in {'detail': '[Errno 111] Connection refused'}
```

`Connection refused` = the test hits the real llama-server on port 8090 (which is not running in CI/default env). This test must be marked `@pytest.mark.integration` like its sibling `test_chat_completions_returns_200` (already marked at line 69).

## 3. Objective
Add `@pytest.mark.integration` to exactly ONE test: `test_chat_completions_returns_correct_format` in `tests/test_rag_server.py`. Do nothing else.

## 4. Scope
- In scope: `ai_workspace/tests/test_rag_server.py`, line 79 only
- Out of scope: every other test, every other file, pytest.ini, README

## 5. Constraints
- Do NOT modify any other test
- Do NOT touch `src/`
- Do NOT run llama-server

## 8. Plan / Execution Steps

### EDIT 1 — `tests/test_rag_server.py` around line 79

**Find:**
```python
    def test_chat_completions_returns_correct_format(self, client):
        """Test chat completions returns expected fields."""
```

**Replace with:**
```python
    @pytest.mark.integration
    def test_chat_completions_returns_correct_format(self, client):
        """Test chat completions returns expected fields."""
```

### FINAL STEP — Verify

Run:
```bash
cd ai_workspace && .venv/bin/python -m pytest tests/test_rag_server.py -v 2>&1 | tail -20
```

Expected: 0 failures in default run (integration-marked tests are deselected). Then:
```bash
cd ai_workspace && .venv/bin/python -m pytest tests/test_rag_server.py -v -m integration 2>&1 | tail -10
```

Expected: exactly 4 tests collected (if pytest.ini has `addopts = -m "not integration"` from TASK-019 v1, use `-m integration` to override).

## 11. Success Criteria (DoD)
- [x] DoD-1: `pytest tests/test_rag_server.py` → 0 failed — evidence: `9 passed, 1 skipped, 8 deselected`
- [x] DoD-2: `@pytest.mark.integration` decorator present at line 79 — already applied (no diff needed for this specific task)

## 13. Change Log
- 2026-04-17 | created | PM | spawn from v1 residual failure
