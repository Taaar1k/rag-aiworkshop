# TASK-025: Directory Scanning & Auto-Indexing Feature

**Status:** Pending  
**Type:** Feature  
**Priority:** High  
**Execution Mode:** Strict  
**Assigned To:** Code Agent  
**Created:** 2026-04-19  
**Research Doc:** [`ai_workspace/docs/DIRECTORY_SCANNING_RESEARCH.md`](../docs/DIRECTORY_SCANNING_RESEARCH.md)

---

## Description

Реалізувати функціонал автоматичного сканування директорій та індексування файлів в RAG-системі. Користувач має змогу вказати шляхи до директорій в конфігураційному файлі (`default.yaml`), і система буде автоматично моніторити ці директорії, індексуючи нові/оновлені файли та видаляючи з індексу видалені файли.

---

## Technical Approach

### Technology Stack (from research)
- **File Watching:** `watchfiles` (Rust-based, async, production-proven)
- **Document Loading:** LangChain `DirectoryLoader` / individual loaders
- **Vector Store:** ChromaDB (PersistentClient) — already in use
- **Background Processing:** asyncio daemon integrated with FastAPI lifecycle
- **Configuration:** YAML (`default.yaml`)
- **State Tracking:** JSON file + SHA256 hashes for incremental indexing

### Architecture

```
FastAPI → asyncio daemon (watchfiles) → IncrementalIndexManager → MemoryManager (ChromaDB)
```

---

## Implementation Steps

### Step 1: Update Configuration (`default.yaml`)

Додати секцію `directory_scanning` до [`ai_workspace/config/default.yaml`](../config/default.yaml):

```yaml
directory_scanning:
  enabled: true
  watched_directories:
    - path: "./data/documents"
      recursive: true
    - path: "./data/knowledge-base"
      recursive: true
  allowed_extensions:
    - ".txt"
    - ".md"
    - ".json"
    - ".csv"
  scan:
    recursive: true
    debounce_ms: 500
    poll_interval_s: 60
  indexing:
    chunk_size: 512
    chunk_overlap: 50
  state:
    persistence_file: "./ai_workspace/memory/index_state.json"
```

### Step 2: Create `DirectoryScannerWorker`

**File:** [`ai_workspace/src/core/directory_scanner.py`](../src/core/directory_scanner.py)

Клас відповідальний за:
- Моніторинг директорій через `watchfiles.awatch()`
- Обробку подій: `Change.added`, `Change.modified`, `Change.deleted`
- Debouncing (фільтрація дубльованих подій)
- Запуск як asyncio daemon task

**Key Methods:**
- `__init__(config: dict, index_manager: IncrementalIndexManager)`
- `start()` — запуск фонових задач
- `stop()` — коректна зупинка
- `_watch_directory(directory_config: dict)` — моніторинг однієї директорії

### Step 3: Create `IncrementalIndexManager`

**File:** [`ai_workspace/src/core/incremental_index_manager.py`](../src/core/incremental_index_manager.py)

Клас відповідальний за:
- Обчислення SHA256 хешів файлів для відстеження змін
- Збереження стану індексації в JSON (`index_state.json`)
- Інкрементне оновлення ChromaDB (видалити старе → додати нове)
- Відновлення стану після перезапуску

**Key Methods:**
- `__init__(config: dict, memory_manager: MemoryManager)`
- `compute_file_hash(filepath: str) -> str`
- `load_state() -> dict`
- `save_state(state: dict) -> None`
- `index_file(filepath: str) -> int` — повертає кількість чанків
- `reindex_file(filepath: str) -> int`
- `delete_from_index(filepath: str) -> int` — видаляє чанки за source
- `initial_scan(directories: list) -> int` — повне сканування при старті

### Step 4: Integrate with `MemoryManager`

**File:** [`ai_workspace/src/core/memory_manager.py`](../src/core/memory_manager.py)

Додати методи до `MemoryManager`:
- `delete_documents_by_source(source: str) -> int` — видаляє всі чанки з `metadata["source"] == source`
- `get_stats_by_source() -> dict` — статистика по джерелах

### Step 5: FastAPI Lifecycle Integration

**File:** [`ai_workspace/src/api/rag_server.py`](../src/api/rag_server.py)

Додати lifecycle hooks:
- `@app.on_event("startup")` — запуск `DirectoryScannerWorker`
- `@app.on_event("shutdown")` — зупинка `DirectoryScannerWorker`

### Step 6: Add `watchfiles` to Dependencies

**File:** [`ai_workspace/requirements.txt`](../requirements.txt)

Додати:
```
watchfiles>=0.21.0
```

---

## DoD (Definition of Done)

### Functional Requirements
- [ ] **DoD-1:** Користувач може додати шляхи до директорій в `default.yaml` у секції `directory_scanning`
- [ ] **DoD-2:** При старті сервера система автоматично сканує всі вказані директорії та індексує файли
- [ ] **DoD-3:** При додаванні нового файлу в monitored директорію, він автоматично індексується протягом `debounce_ms`
- [ ] **DoD-4:** При зміні файлу, він переіндексується (старі чанки видаляються, нові додаються)
- [ ] **DoD-5:** При видаленні файлу, його чанки видаляються з ChromaDB
- [ ] **DoD-6:** Підтримуються розширення: `.txt`, `.md`, `.json`, `.csv` (з case-insensitive перевіркою)
- [ ] **DoD-7:** Система коректно обробляє рекурсивні директорії
- [ ] **DoD-8:** Стан індексації зберігається в JSON і відновлюється після перезапуску

### Non-Functional Requirements
- [ ] **DoD-9:** Сканер працює в окремому asyncio task, не блокуючи основний сервер
- [ ] **DoD-10:** Debouncing реалізовано (події від однієї зміни обробляються один раз)
- [ ] **DoD-11:** Помилки індексації не падають з павніком, а логується
- [ ] **DoD-12:** Конфігурація `enabled: false` повністю вимикає сканер

### Testing Requirements
- [ ] **DoD-13:** Unit-тести для `IncrementalIndexManager` (hash, save/load state, index/reindex/delete)
- [ ] **DoD-14:** Unit-тести для `DirectoryScannerWorker` (mock watchfiles events)
- [ ] **DoD-15:** Integration-тест: створити тимчасову директорію → додати файл → перевірити індекс
- [ ] **DoD-16:** Тест на коректне видалення чанків при видаленні файлу

### Documentation Requirements
- [ ] **DoD-17:** Оновлено [`ai_workspace/docs/UKRAINIAN_OVERVIEW.md`](../docs/UKRAINIAN_OVERVIEW.md) з розділом про directory scanning
- [ ] **DoD-18:** Docstrings для всіх пекласів і методів в Python docstring форматі

---

## File Structure

```
ai_workspace/
├── config/
│   └── default.yaml (updated)
├── src/
│   └── core/
│       ├── memory_manager.py (updated)
│       ├── directory_scanner.py (new)
│       └── incremental_index_manager.py (new)
├── api/
│   └── rag_server.py (updated)
├── tests/
│   └── test_directory_scanner.py (new)
│   └── test_incremental_index_manager.py (new)
├── memory/
│   └── index_state.json (created at runtime)
└── docs/
    └── UKRAINIAN_OVERVIEW.md (updated)
```

---

## Dependencies

- `watchfiles>=0.21.0` — додати в `requirements.txt`
- Існуючі: `chromadb`, `langchain`, `langchain_chroma`, `fastapi`, `uvicorn`

---

## Notes

- Використовувати існуючу `MemoryManager` для взаємодії з ChromaDB
- Стан індексації (`index_state.json`) має зберігати: `filepath -> sha256_hash` мапу
- При перезапуску: порівняти поточний стан файлів зі збереженим хешами
- Debounce час: 500ms (конфігурується)
- Poll interval (fallback): 60s (періодична перевірка як backup)
