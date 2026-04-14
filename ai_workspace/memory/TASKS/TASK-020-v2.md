# TASK-020 v2: MemoryPersistence — restore `use_memory_fallback` semantics, fix crash test via fixture

## 1. Metadata
- Task ID: TASK-020-v2
- Created: 2026-04-17
- Assigned to: Code
- Mode: light (prescriptive)
- Status: DONE
- Priority: P1

## 2. Context
TASK-020 v1 tried to fix `test_crash_during_save_recovery` by making `save_conversation` write to disk even when `use_memory_fallback=True`. This broke the contract: `use_memory_fallback=True` means "do NOT touch disk; keep everything in memory." As a result **4 tests now fail** that were previously passing:

1. `tests/test_memory_persistence.py::TestMemoryPersistenceMemoryFallback::test_memory_fallback_no_file_created`
   - Asserts: no file is created when `use_memory_fallback=True`
   - Now fails because save writes to disk
2. `tests/test_crash_stress.py::TestMemoryPersistenceStress::test_1000_concurrent_sessions`
3. `tests/test_crash_stress.py::TestRecoveryTests::test_concurrent_recovery`
4. `tests/test_crash_stress.py::TestComprehensiveStressTest::test_full_stress_scenario`
   - All three do heavy concurrent save/load with `use_memory_fallback=True` and now either race on disk or fail checksums

**The correct contract:**
- `use_memory_fallback=True` → store in-process dict ONLY, never touch disk. Fast, volatile. Used for concurrent stress/perf tests.
- `use_memory_fallback=False` → persist to `storage_path` JSON on every `save_conversation` call when `auto_save=True`. Survives process restart.

The original intent of `test_crash_during_save_recovery` is **disk persistence** (simulate crash → new process → data survives). It uses the wrong fixture flag. Fix: flip `use_memory_fallback=True` → `False` in that one test.

## 3. Objective
1. Revert `src/core/memory_persistence.py` to the behavior where `use_memory_fallback=True` never writes to disk.
2. Change `test_crash_during_save_recovery` fixture to use `use_memory_fallback=False` (disk-backed) — that's what the test actually needs.

## 4. Scope
- In scope:
  - `ai_workspace/src/core/memory_persistence.py` (revert any TASK-020 v1 disk-write changes under the `use_memory_fallback=True` branch)
  - `ai_workspace/tests/test_crash_stress.py` — line 729-747, exactly 2 `use_memory_fallback=True` → `False`
- Out of scope: every other test, every other file

## 5. Constraints
- Do NOT modify any other test that uses `use_memory_fallback=True`
- Do NOT change the public API of `MemoryPersistence`
- After all edits, **0 failures** in `test_memory_persistence.py` AND `test_crash_stress.py`

## 8. Plan / Execution Steps

### EDIT 1 — Revert `src/core/memory_persistence.py`

Open the file. Find the `save_conversation` method (and any helper it calls). Ensure the code path looks like:

```python
def save_conversation(self, messages, session_id):
    # ... build payload ...
    if self.use_memory_fallback:
        self._memory_store[session_id] = messages
        return  # NEVER touch disk in fallback mode
    # disk path
    with open(self.storage_path, "w") as f:
        json.dump(payload, f)
```

If TASK-020 v1 added `else`-less disk writes or duplicated the disk path inside the `use_memory_fallback` branch, remove them. The fallback branch must be pure in-memory and return without I/O.

If `__init__` loads existing file contents into `_memory_store` when `use_memory_fallback=True` — that's fine (allows sharing state across instances that point to same path, but only via re-reading on init). If that was added in v1, leave it; it's harmless for the fallback contract as long as **save** is memory-only.

After the edit, the contract holds: with `use_memory_fallback=True`, no new file should ever be written.

### EDIT 2 — `tests/test_crash_stress.py` lines 729-747

**Find:**
```python
    def test_crash_during_save_recovery(self, temp_storage_path):
        """Simulate crash during save and verify recovery."""
        persistence = MemoryPersistence(
            storage_path=temp_storage_path,
            use_memory_fallback=True,
            auto_save=True
        )
        
        # Save initial data
        messages1 = [
            Message(role="user", content="Before crash", timestamp="2026-04-15T10:00:00")
        ]
        persistence.save_conversation(messages1, "crash_test_session")
        
        # Simulate crash by creating a new persistence instance
        # (simulating restart after crash)
        new_persistence = MemoryPersistence(
            storage_path=temp_storage_path,
            use_memory_fallback=True,
            auto_save=True
        )
```

**Replace with:**
```python
    def test_crash_during_save_recovery(self, temp_storage_path):
        """Simulate crash during save and verify recovery.

        Uses disk-backed persistence (use_memory_fallback=False) because the
        test simulates a process restart — data must survive to disk.
        """
        persistence = MemoryPersistence(
            storage_path=temp_storage_path,
            use_memory_fallback=False,
            auto_save=True
        )

        # Save initial data
        messages1 = [
            Message(role="user", content="Before crash", timestamp="2026-04-15T10:00:00")
        ]
        persistence.save_conversation(messages1, "crash_test_session")

        # Simulate crash by creating a new persistence instance
        # (simulating restart after crash)
        new_persistence = MemoryPersistence(
            storage_path=temp_storage_path,
            use_memory_fallback=False,
            auto_save=True
        )
```

### FINAL STEP — Verify

Run:
```bash
cd ai_workspace && .venv/bin/python -m pytest tests/test_memory_persistence.py tests/test_crash_stress.py -v 2>&1 | tail -30
```

Expected:
- `test_memory_fallback_no_file_created` → PASS
- `test_crash_during_save_recovery` → PASS
- `test_1000_concurrent_sessions` → PASS
- `test_concurrent_recovery` → PASS
- `test_full_stress_scenario` → PASS

Full summary line should say **0 failed**.

**Execution Result (2026-04-17):**
- All 51 tests passed, 0 failed
- Key tests: `test_memory_fallback_no_file_created` PASSED, `test_crash_during_save_recovery` PASSED, `test_1000_concurrent_sessions` PASSED, `test_concurrent_recovery` PASSED, `test_full_stress_scenario` PASSED
- Summary: `51 passed, 1 warning in 4.28s`

## 11. Success Criteria (DoD)
- [x] DoD-1: `pytest tests/test_memory_persistence.py tests/test_crash_stress.py` → 0 failed — evidence: `51 passed, 1 warning in 4.28s`
- [x] DoD-2: `git diff src/core/memory_persistence.py` shows revert of disk-write-under-fallback added in v1 — `_write_to_file` no longer calls `_write_to_file_disk_only` under `use_memory_fallback=True`
- [x] DoD-3: `git diff tests/test_crash_stress.py` shows exactly 2 flag flips (True→False) at lines 735 and 749 (adjusted for docstring expansion)
- [x] DoD-4: Change Log entries for EDIT 1 and EDIT 2 added

## 13. Change Log
- 2026-04-17 | EDIT 1 | Code | Reverted `_write_to_file` in `src/core/memory_persistence.py`: removed `_write_to_file_disk_only` call under `use_memory_fallback=True` branch — now pure in-memory, never touches disk
- 2026-04-17 | EDIT 2 | Code | Fixed `test_crash_during_save_recovery` in `tests/test_crash_stress.py`: flipped `use_memory_fallback=True` → `False` at lines 735 and 749 (adjusted for docstring expansion), added explanatory docstring
- 2026-04-17 | created | PM | v1 broke `use_memory_fallback` contract; v2 restores it and fixes the one test that needs disk persistence
