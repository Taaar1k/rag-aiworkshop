# TASK-037: Fix venv deps + test discovery (7 collection errors)

## 1. Metadata
- Task ID: TASK-037
- Title: Fix venv deps + test discovery (7 collection errors)
- Related SPEC: SPEC-2026-04-20-PRODUCTION-HARDENING
- Assigned To: Debug
- Mode: strict
- Priority: P0 (blocks all subsequent DoD verification)
- Estimated effort: 30 min
- Status: DONE

## 2. Problem Statement

**Symptom:** 7 test files failed collection in a fresh venv:
- `test_crash_stress.py`
- `test_hybrid_retriever.py`
- `test_integration_hybrid_search.py`
- `test_multimodal_image_encoder.py`
- `test_multimodal_image_preprocessor.py`
- `test_multimodal_multimodal_llm.py`
- `test_multimodal_unified_retriever.py`

**Root cause:** Missing deps (`rank_bm25`, `PIL`, `torch`, `langchain-core`) + inconsistent `sys.path` manipulation across tests + incorrect relative import in `unified_retriever.py`.

## 3. DoD (Definition of Done)

- [x] Fresh venv + `pip install -r requirements.txt` + `pytest tests/ --collect-only` → 0 errors
- [x] No `sys.path.insert` in any `tests/*.py`
- [x] README badge count matches actual passing count (verified separately in TASK-032)

## 4. Root Cause Analysis

### 4.1 Missing Dependencies
The root `requirements.txt` was missing:
- `torch` — required by multimodal tests (`test_multimodal_*.py`)
- `Pillow` (PIL) — required by multimodal tests
- `rank_bm25` — required by BM25 retriever tests
- `langchain-core` — required for `langchain_core.documents.Document` imports
- `pytest` — required for test collection

### 4.2 sys.path.insert in 18 Test Files
All test files used per-file `sys.path.insert` instead of relying on pytest configuration:
- `test_crash_stress.py`, `test_hybrid_retriever.py`, `test_integration_hybrid_search.py`
- `test_memory_persistence.py`, `test_service_orchestrator.py`, `test_graph_integration.py`
- `test_incremental_index_manager.py`, `test_entity_extractor.py`, `test_directory_scanner.py`
- `test_graph_retriever.py`, `test_agents.py`, `test_rag_evaluator.py`
- `test_rate_limiter.py`, `test_health_check.py`
- `test_multimodal_image_encoder.py`, `test_multimodal_image_preprocessor.py`
- `test_multimodal_multimodal_llm.py`, `test_multimodal_unified_retriever.py`

### 4.3 Incorrect pytest.ini pythonpath
`pytest.ini` was missing `pythonpath` configuration, so pytest couldn't find the `src` module.

### 4.4 Broken Relative Import in Source
`src/multimodal/unified_retriever.py` line 10 had `from ..multimodal.image_encoder import ImageEncoder` which fails when `src` is on `pythonpath` (relative import beyond top-level package).

## 5. Fix Summary

### 5.1 requirements.txt — Added Missing Deps
```
torch
Pillow
rank_bm25
langchain-core
pytest
```

### 5.2 pytest.ini — Added pythonpath
```ini
pythonpath = src
```
Also added `optional` marker for tests requiring optional deps (CLIP/PIL).

### 5.3 Removed sys.path.insert from 18 Test Files
All `sys.path.insert(0, ...)` lines removed from all test files.

### 5.4 Fixed Relative Import in unified_retriever.py
Changed `from ..multimodal.image_encoder import ImageEncoder` to `from .image_encoder import ImageEncoder`.

## 6. Evidence

### 6.1 sys.path.insert Grep (0 hits)
```
$ cd ai_workspace && grep -r "sys\.path\.insert" tests/
# Exit code: 1 (no matches)
```

### 6.2 Test Collection (0 errors)
```
$ cd ai_workspace && python -m pytest tests/ --collect-only
collected 409 items / 8 deselected / 401 selected
=============== 401/409 tests collected (8 deselected) in 3.13s ================
```
Note: 8 deselected are integration tests (filtered by `-m "not integration"`).

## 7. Files Modified

| File | Change |
|------|--------|
| `requirements.txt` | Added 5 missing deps |
| `ai_workspace/pytest.ini` | Added `pythonpath = src`, added `optional` marker |
| `ai_workspace/src/multimodal/unified_retriever.py` | Fixed relative import |
| `ai_workspace/tests/test_crash_stress.py` | Removed sys.path.insert |
| `ai_workspace/tests/test_hybrid_retriever.py` | Removed sys.path.insert |
| `ai_workspace/tests/test_integration_hybrid_search.py` | Removed sys.path.insert |
| `ai_workspace/tests/test_memory_persistence.py` | Removed sys.path.insert |
| `ai_workspace/tests/test_service_orchestrator.py` | Removed sys.path.insert |
| `ai_workspace/tests/test_graph_integration.py` | Removed sys.path.insert |
| `ai_workspace/tests/test_incremental_index_manager.py` | Removed sys.path.insert |
| `ai_workspace/tests/test_entity_extractor.py` | Removed sys.path.insert |
| `ai_workspace/tests/test_directory_scanner.py` | Removed sys.path.insert |
| `ai_workspace/tests/test_graph_retriever.py` | Removed sys.path.insert |
| `ai_workspace/tests/test_agents.py` | Removed sys.path.insert |
| `ai_workspace/tests/test_rag_evaluator.py` | Removed sys.path.insert |
| `ai_workspace/tests/test_rate_limiter.py` | Removed sys.path.insert |
| `ai_workspace/tests/test_health_check.py` | Removed sys.path.insert |
| `ai_workspace/tests/test_multimodal_image_encoder.py` | Removed sys.path.insert |
| `ai_workspace/tests/test_multimodal_image_preprocessor.py` | Removed sys.path.insert |
| `ai_workspace/tests/test_multimodal_multimodal_llm.py` | Removed sys.path.insert |
| `ai_workspace/tests/test_multimodal_unified_retriever.py` | Removed sys.path.insert |

## 8. Change Log
- 2026-04-20: TASK-037 DONE — All 401 tests collected with 0 errors, 0 sys.path.insert remaining
