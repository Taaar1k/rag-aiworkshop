# TASK-019: Mark llama.cpp-Dependent RAG Server Tests as Integration

## 1. Metadata
- Task ID: TASK-019
- Created: 2026-04-16
- Assigned to: Code
- Mode: light
- Status: TODO
- Priority: P1 (blocks clean CI output)

## 2. Context
Three tests in `tests/test_rag_server.py` fail because they require a real llama.cpp model runtime. Failures are not logic bugs — they're environment dependencies:

```
FAILED tests/test_rag_server.py::TestChatCompletions::test_chat_completions_returns_200
FAILED tests/test_rag_server.py::TestModelLoading::test_llm_initialization
FAILED tests/test_rag_server.py::TestErrorHandling::test_invalid_request_returns_422
```

Root symptom: `AttributeError: 'LlamaModel' object has no attribute 'sampler'` — raised during deallocation of a partially-initialized `llama_cpp.Llama` instance, indicating the model file wasn't loaded successfully in the test environment.

These tests are **integration tests** — they need a GGUF model on disk and working llama-cpp bindings. They don't belong in the default unit-test run.

## 3. Objective
Mark the three failing tests with `@pytest.mark.integration`, configure `pytest.ini` so default runs exclude integration-marked tests, and document the opt-in command for running them.

## 4. Scope
- In scope:
  - Add `@pytest.mark.integration` decorator to the 3 failing tests (or to their test classes)
  - Create/update `pytest.ini` with `markers = integration: ...` and `addopts = -m "not integration"`
  - Update root `README.md` with `pytest` and `pytest -m integration` commands
- Out of scope:
  - Fixing the underlying llama.cpp binding issue
  - Creating mock-based versions of these tests

## 5. Constraints
- Must not hide tests that currently pass — only mark the 3 confirmed failing ones
- Must still allow `pytest -m integration` to run all integration tests together
- Must finish in ≤ 20 min

## 6. Options Considered
<!-- Ask agent fills if decision needed -->

## 7. Decision and Rationale
<!-- Ask agent fills if decision needed -->

## 8. Plan / Execution Steps
- [x] Add `@pytest.mark.integration` decorator to 3 failing tests in [`test_rag_server.py`](ai_workspace/tests/test_rag_server.py:69)
- [x] Create [`pytest.ini`](ai_workspace/pytest.ini) with integration marker and default exclude
- [x] Update [`README.md`](README.md:63) Testing section with pytest commands
- [x] Verify `pytest tests/` runs without llama.cpp failures (297 passed, 2 unrelated failures)
- [x] Verify `pytest tests/ -m integration` runs the 3 marked tests (3 failed as expected)

## 9. Risks
- R1: Other tests in `test_rag_server.py` may also be llama-dependent but currently passing by accident — Code should run the file twice after marking to confirm stability
- R2: `pytest.ini` may already exist with conflicting config — check before creating

## 10. Dependencies
- `pytest.ini` (may or may not exist at repo root or `ai_workspace/`)
- `tests/test_rag_server.py` (to be edited)
- `README.md` (to be updated — check TASK-021 for README ownership)

## 11. Success Criteria (DoD)
- [x] DoD-1: `pytest tests/` (default run) reports 0 failures related to llama.cpp — evidence: pytest summary (297 passed, 2 unrelated failures in test_crash_stress.py)
- [x] DoD-2: `pytest tests/ -m integration` runs the 3 marked tests explicitly — evidence: pytest collected=3 output
- [x] DoD-3: `pytest.ini` exists with `integration` marker registered and default exclude — evidence: file contents + pytest warning-free run
- [x] DoD-4: README has a Testing section describing both commands — evidence: README diff
- [x] DoD-5: Change Log shows per-test marking rationale

## 12. Open Questions
- Should `TestSecurityIntegration` tests from TASK-018 also be moved under the same `integration` marker once TASK-018 is DONE? (Defer decision to PM after TASK-018 completes.)

## 13. Change Log
- 2026-04-16 | created | PM created task based on pytest environment-dependent failures | Task-019 added to TASK_BOARD
- 2026-04-16 | executed | Code agent marked 3 failing tests with `@pytest.mark.integration` | [`test_rag_server.py`](ai_workspace/tests/test_rag_server.py:69) updated
- 2026-04-16 | executed | Code agent created [`pytest.ini`](ai_workspace/pytest.ini) with integration marker and default exclude | pytest.ini created
- 2026-04-16 | executed | Code agent updated [`README.md`](README.md:63) Testing section | README.md updated
- 2026-04-16 | verified | Default pytest run: 297 passed, 2 unrelated failures | No llama.cpp failures in default run
- 2026-04-16 | verified | Integration pytest run: 3 tests collected, 3 failed as expected | Integration tests properly excluded from default run
