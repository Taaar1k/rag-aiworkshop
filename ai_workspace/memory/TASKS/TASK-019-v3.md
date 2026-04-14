# TASK-019 v3: Mark remaining 2 env-dependent tests in test_rag_server.py

## 1. Metadata
- Task ID: TASK-019-v3
- Created: 2026-04-17
- Assigned to: Code
- Mode: light (prescriptive)
- Status: DONE
- Priority: P1

## 2. Context
After v2, full `pytest tests/` still shows 2 failures, both in `tests/test_rag_server.py`:

1. `TestRAGQuery::test_rag_query_returns_200` — `[Errno 111] Connection refused` (llama-server not running). Real llama dependency → belongs to `integration` marker.
2. `TestPerformance::test_embedding_latency` — `5.07s > 5.0s` threshold. The test downloads a real HuggingFace model on first run; the 5s budget is too tight for cold-start on slow networks. Simplest fix: also mark it `integration` (it depends on a real embedding model being loadable), AND at the same time raise the threshold to 10s so that when it IS run in the integration pass, it's not flaky.

## 3. Objective
Add `@pytest.mark.integration` to both tests. Raise the latency threshold in `test_embedding_latency` to `10.0`.

## 4. Scope
- In scope: `ai_workspace/tests/test_rag_server.py` — exactly 3 edits
- Out of scope: everything else

## 5. Constraints
- Do NOT touch `src/`
- Do NOT modify any test not listed here

## 8. Plan / Execution Steps

### EDIT 1 — `test_rag_server.py` around line 139 (`test_rag_query_returns_200`)

**Find:**
```python
    def test_rag_query_returns_200(self, client):
        """Test RAG query returns 200 OK."""
```

**Replace with:**
```python
    @pytest.mark.integration
    def test_rag_query_returns_200(self, client):
        """Test RAG query returns 200 OK."""
```

### EDIT 2 — `test_rag_server.py` around line 148 (`test_rag_query_returns_correct_format`)

Check this test: it also calls `/rag/query` with `client.post`. Same connection issue will hit. Mark it integration too.

**Find:**
```python
    def test_rag_query_returns_correct_format(self, client):
```

**Replace with:**
```python
    @pytest.mark.integration
    def test_rag_query_returns_correct_format(self, client):
```

### EDIT 3 — `test_rag_server.py` around line 248 (`test_embedding_latency`)

**Find:**
```python
    def test_embedding_latency(self, client):
        """Test embedding generation responds within 1 second."""
        import time
        request = {
            "model": "nomic-embed-text-v1.5",
            "input": "Test text"
        }
        start = time.time()
        response = client.post("/v1/embeddings", json=request)
        elapsed = time.time() - start
    
        assert response.status_code == 200
        # Allow longer time if embedding model needs to load
        assert elapsed < 5.0  # 5 second threshold for first load
```

**Replace with:**
```python
    @pytest.mark.integration
    def test_embedding_latency(self, client):
        """Test embedding generation responds within a reasonable budget.

        Marked integration because it downloads a real HuggingFace model
        on first run. The 10s budget accommodates cold-start on slow links.
        """
        import time
        request = {
            "model": "nomic-embed-text-v1.5",
            "input": "Test text"
        }
        start = time.time()
        response = client.post("/v1/embeddings", json=request)
        elapsed = time.time() - start

        assert response.status_code == 200
        assert elapsed < 10.0  # generous threshold for first load
```

### EDIT 4 — check `test_full_rag_flow` around line 268

If this test also hits `/rag/query` or `/v1/chat/completions`, it will fail for the same reason. If so, mark it integration with the same decorator. If it doesn't hit those endpoints, leave alone.

### FINAL STEP — Verify

Run:
```bash
cd ai_workspace && .venv/bin/python -m pytest tests/ 2>&1 | tail -5
```

Expected summary line: `0 failed` (pass count = 296 + embedding_latency was previously passing sometimes, so may be 296 or 295; skipped/deselected will rise).

## 11. Success Criteria (DoD)
- [x] DoD-1: `pytest tests/` → **0 failed** — evidence: `295 passed, 1 skipped, 8 deselected`
- [x] DoD-2: `pytest tests/ -m integration` collects all integration tests without error — evidence: `4 passed, 3 failed, 1 skipped, 296 deselected` (3 failures expected — llama-server not running)
- [x] DoD-3: Change Log per edit

## 13. Change Log
- 2026-04-17 | created | PM | after v2, 2 residual env-dependent failures in test_rag_server.py
- 2026-04-17 | EDIT 1 | Code | Added `@pytest.mark.integration` to `test_rag_query_returns_200` (line 140) — evidence: git diff line +79
- 2026-04-17 | EDIT 2 | Code | Added `@pytest.mark.integration` to `test_rag_query_returns_correct_format` (line 149) — evidence: git diff line +147
- 2026-04-17 | EDIT 3 | Code | Added `@pytest.mark.integration` to `test_embedding_latency` (line 251) + raised threshold from 5.0 to 10.0 — evidence: git diff lines +251,+253-258,+266
- 2026-04-17 | EDIT 4 | Code | Added `@pytest.mark.integration` to `test_full_rag_flow` (line 275) — evidence: git diff line +275
- 2026-04-17 | VERIFY | Code | DoD-1: `pytest tests/` → 295 passed, 1 skipped, 8 deselected, 0 failed
- 2026-04-17 | VERIFY | Code | DoD-2: `pytest tests/ -m integration` → 4 passed, 3 failed (expected), 1 skipped, 296 deselected
