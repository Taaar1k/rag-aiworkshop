# TASK-020: MemoryPersistence loses data across instance restarts

## 1. Metadata
- Task ID: TASK-020
- Created: 2026-04-16
- Assigned to: Debug
- Mode: strict
- Status: TODO
- Priority: P1

## 2. Context
`tests/test_crash_stress.py::TestRecoveryTests::test_crash_during_save_recovery` fails with:

```
>       assert len(loaded) == 1
E       assert 0 == 1
E        +  where 0 = len([])
tests/test_crash_stress.py:751: AssertionError
```

The test:
1. Instantiates `MemoryPersistence(storage_path, use_memory_fallback=True, auto_save=True)`
2. Saves one message under `crash_test_session`
3. Creates a fresh `MemoryPersistence` with the **same** `storage_path` (simulating restart)
4. Loads `crash_test_session` — expects 1 message, gets 0

Captured stdout: `Conversation saved in 0.000s` — the first save reports success, but the second instance sees an empty file/store.

This is a real bug in `MemoryPersistence`, not a test/API mismatch. TASK-017 marked this test INSUFFICIENT_DATA per R2.

## 3. Objective
Diagnose whether `auto_save=True` with `use_memory_fallback=True` actually writes to disk, or whether data is kept in memory only and lost when a second instance starts.

## 4. Scope
- In scope:
  - `ai_workspace/src/core/memory_persistence.py` (or equivalent module)
  - `ai_workspace/tests/test_crash_stress.py::TestRecoveryTests::test_crash_during_save_recovery`
- Out of scope: unrelated persistence features (search, pruning, compaction)

## 5. Constraints
- Do not change the test's intent (data must survive a restart when `auto_save=True`)
- If `use_memory_fallback=True` is intentionally in-memory-only, the test should be updated to use `use_memory_fallback=False` **and** the docstring of the parameter must be clarified
- Reproduce and root-cause before patching

## 8. Plan / Execution Steps
1. Read `MemoryPersistence.__init__`, `save_conversation`, `load_conversation`
2. Determine whether `use_memory_fallback=True` writes to disk at all
3. Decide: fix the persistence code, or change the test's fixture flag (document rationale either way)
4. Re-run: `pytest tests/test_crash_stress.py::TestRecoveryTests::test_crash_during_save_recovery -v`

## 11. Success Criteria (DoD)
- [ ] DoD-1: `test_crash_during_save_recovery` passes — evidence: pytest summary line
- [ ] DoD-2: Root cause documented in Change Log (code bug vs. test-fixture bug)
- [ ] DoD-3: If production code changed, no regressions in rest of `test_crash_stress.py` (still ≥24 passed)

## 13. Change Log
- 2026-04-16 | created | PM | spawned from TASK-017 R2 (INSUFFICIENT_DATA for this one test)
