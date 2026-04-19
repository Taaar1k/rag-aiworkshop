# Directory Scanning Research for RAG System

**Date:** 2026-04-19  
**Author:** Scaut Agent  
**Status:** Complete  

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Directory Watching Libraries Comparison](#2-directory-watching-libraries-comparison)
3. [Incremental Indexing Strategies](#3-incremental-indexing-strategies)
4. [Configuration-Based Directory Paths](#4-configuration-based-directory-paths)
5. [File Extension Filtering](#5-file-extension-filtering)
6. [Background Worker Patterns](#6-background-worker-patterns)
7. [ChromaDB/LangChain Integration](#7-chromadblangchain-integration)
8. [Recommendations](#8-recommendations)
9. [References](#9-references)

---

## 1. Executive Summary

This research covers six critical topics for implementing directory scanning functionality in the RAG system. The primary recommendation is to use **watchfiles** (Rust-based, async) combined with **LangChain DirectoryLoader** for document loading and **ChromaDB upsert** for incremental indexing. For background processing, an **asyncio-based daemon pattern** integrated with FastAPI lifecycle events is recommended.

---

## 2. Directory Watching Libraries Comparison

### 2.1 Watchdog

**Source:** [`watchdog`](https://pypi.org/project/watchdog/) (PyPI), [GitHub](https://github.com/gorakhargosh/watchdog)

Watchdog is the most established Python filesystem monitoring library with cross-platform support (Windows, macOS, Linux).

**Basic Example:**

```python
import time
from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer

class RAGFileEventHandler(FileSystemEventHandler):
    def on_created(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            print(f"[NEW] {event.src_path}")
            
    def on_modified(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            print(f"[MODIFIED] {event.src_path}")
            
    def on_deleted(self, event: FileSystemEvent) -> None:
        if not event.is_directory:
            print(f"[DELETED] {event.src_path}")

event_handler = RAGFileEventHandler()
observer = Observer()
observer.schedule(event_handler, "./documents", recursive=True)
observer.start()

try:
    while True:
        time.sleep(1)
finally:
    observer.stop()
    observer.join()
```

**Advanced Pattern (Multiple Directories):**

```python
from watchdog.observers import Observer
from watchdog.events import PatternMatchingEventHandler, FileSystemEvent

class RAGDocumentHandler(PatternMatchingEventHandler):
    def __init__(self, allowed_extensions):
        patterns = [f"*.{ext}" for ext in allowed_extensions]
        super().__init__(patterns=patterns, ignore_directories=True)
        self.allowed_extensions = allowed_extensions

    def on_modified(self, event: FileSystemEvent) -> None:
        print(f"[UPDATED] {event.src_path}")
        # Trigger incremental indexing

    def on_created(self, event: FileSystemEvent) -> None:
        print(f"[NEW] {event.src_path}")
        # Trigger indexing

observer = Observer()
handler = RAGDocumentHandler(["txt", "md", "json", "csv"])
observer.schedule(handler, "./documents", recursive=True)
observer.start()
```

**Directory Snapshot Comparison:**

```python
from watchdog.utils.dirsnapshot import DirectorySnapshot, DirectorySnapshotDiff
import time

# Initial snapshot
snapshot1 = DirectorySnapshot(path="./documents", recursive=True)

# ... wait for changes ...
time.sleep(5)

# Compare
snapshot2 = DirectorySnapshot(path="./documents", recursive=True)
diff = DirectorySnapshotDiff(snapshot1, snapshot2)

print(f"Files added: {diff.files_added}")
print(f"Files removed: {diff.files_removed}")
print(f"Files modified: {diff.files_modified}")
```

**Pros:**
- Mature, well-documented, widely used
- Cross-platform support
- Rich event types (create, modify, delete, moved)
- Pattern matching and regex filtering
- Directory snapshot utilities for polling-based comparison

**Cons:**
- Pure Python (slower than Rust-based alternatives)
- Uses OS-level APIs (inotify on Linux, FSEvents on macOS, ReadDirectoryChangesW on Windows)
- No native async support
- Higher resource usage on large directory trees

---

### 2.2 watchfiles

**Source:** [`watchfiles`](https://watchfiles.helpmanual.io/), [GitHub](https://github.com/samuelcolvin/watchfiles)

watchfiles is a modern, high-performance file watcher built on Rust's Notify library. It's the same library that powers uvicorn auto-reload.

**Basic Async Example:**

```python
import asyncio
from watchfiles import awatch, Change

async def main():
    async for changes in awatch('./documents', recursive=True):
        for change_type, path in changes:
            if change_type == Change.added:
                print(f"[NEW] {path}")
            elif change_type == Change.modified:
                print(f"[MODIFIED] {path}")
            elif change_type == Change.deleted:
                print(f"[DELETED] {path}")

asyncio.run(main())
```

**With Debouncing and Filtering:**

```python
import asyncio
from pathlib import Path
from watchfiles import awatch, Change, stop_event_checker

ALLOWED_EXTENSIONS = {'.txt', '.md', '.json', '.csv'}

async def watch_documents():
    async for changes in awatch(
        './documents',
        recursive=True,
        watch_filter=(
            lambda change: Path(change[1]).suffix.lower() in ALLOWED_EXTENSIONS
        ),
        debounce=500,  # 500ms debounce
        sleep=0.1,
    ):
        for change_type, path in changes:
            print(f"[{Change(change_type).name}] {path}")
            # Process change

asyncio.run(watch_documents())
```

**Pros:**
- Rust-based, significantly faster than watchdog
- Native async/await support
- Automatic fallback to polling when OS notifications unavailable
- Built-in debouncing
- Used by uvicorn, fastapi, and other production tools
- Lower resource usage

**Cons:**
- Newer library (less battle-tested than watchdog)
- Requires Rust compilation for installation on some platforms
- Smaller community and fewer examples

---

### 2.3 inotify (Linux Native)

**Source:** [Linux inotify documentation](https://man7.org/linux/man-pages/man7/inotify.7.html)

inotify is a Linux kernel subsystem for monitoring filesystem events. It's accessed via watchdog on Linux (watchdog uses inotify_backend).

**Direct Python Access (via pyinotify):**

```python
import pyinotify

class Handler(pyinotify.ProcessEvent):
    def process_IN_CREATE(self, event):
        print(f"Created: {event.name}")
    
    def process_IN_MODIFY(self, event):
        print(f"Modified: {event.name}")
    
    def process_IN_DELETE(self, event):
        print(f"Deleted: {event.name}")

wm = pyinotify.WatchManager()
wm.add_watch('./documents', pyinotify.ALL_EVENTS, rec=True)
nh = pyinotify.Notifier(wm, Handler())
nh.loop()
```

**Pros:**
- Most performant on Linux (kernel-level)
- Low latency
- Fine-grained control

**Cons:**
- Linux-only (not cross-platform)
- Requires pyinotify dependency
- watchdog already wraps inotify on Linux, so direct use is rarely needed

---

### 2.4 Comparison Summary

| Feature | Watchdog | watchfiles | inotify/pyinotify |
|---------|----------|------------|-------------------|
| Performance | Medium | High | Highest |
| Cross-platform | Yes | Yes | Linux only |
| Async support | No | Yes | No |
| Maturity | Very High | Medium | High |
| Resource usage | Medium | Low | Low |
| Auto-reload | No | Yes (arun_process) | No |
| Debouncing | Manual | Built-in | Manual |
| Production use | Very common | Growing (uvicorn) | Legacy |

### 2.5 Recommendation

**For production RAG system: `watchfiles`**

Reasons:
1. Native async support integrates seamlessly with FastAPI
2. Rust-based performance is superior for large document directories
3. Built-in debouncing prevents excessive indexing triggers
4. Already proven in production (uvicorn, FastAPI ecosystem)
5. Lower resource footprint for long-running daemon

**Fallback option:** Use watchdog if cross-platform compatibility is critical and watchfiles installation fails.

---

## 3. Incremental Indexing Strategies

### 3.1 Strategy 1: Filesystem Event-Driven (Recommended)

Track changes via filesystem events and index only affected files.

```python
import hashlib
from pathlib import Path
from typing import Dict, Set
import asyncio
from watchfiles import awatch, Change

class IncrementalIndexManager:
    def __init__(self, vector_store, embedding_function):
        self.vector_store = vector_store
        self.embedding_function = embedding_function
        self.file_hashes: Dict[str, str] = {}  # path -> hash
        self.processed_files: Set[str] = set()
    
    def compute_file_hash(self, filepath: str) -> str:
        """Compute SHA256 hash of file content."""
        with open(filepath, 'rb') as f:
            return hashlib.sha256(f.read()).hexdigest()
    
    async def index_new_or_changed(self, filepath: str) -> bool:
        """Index a file only if it's new or modified."""
        file_hash = self.compute_file_hash(filepath)
        
        if filepath in self.file_hashes:
            if self.file_hashes[filepath] == file_hash:
                print(f"Unchanged: {filepath}")
                return False
            else:
                print(f"Changed: {filepath}")
                # Remove old entry and re-index
                await self._remove_from_vector_store(filepath)
        else:
            print(f"New file: {filepath}")
        
        # Index the file
        await self._index_file(filepath)
        self.file_hashes[filepath] = file_hash
        self.processed_files.add(filepath)
        return True
    
    async def _remove_from_vector_store(self, filepath: str):
        """Remove documents associated with a file."""
        # ChromaDB: query by metadata source
        results = self.vector_store.similarity_search_with_score(
            query="", k=100,
            filter={"source": str(filepath)}
        )
        # Delete by IDs (requires storing document IDs)
        # ...
    
    async def _index_file(self, filepath: str):
        """Load and index a single file."""
        from langchain.document_loaders import (
            TextLoader, JSONLoader, CSVLoader, UnstructuredMarkdownLoader
        )
        
        ext = Path(filepath).suffix.lower()
        loader_map = {
            '.txt': lambda: TextLoader(filepath),
            '.md': lambda: UnstructuredMarkdownLoader(filepath),
            '.json': lambda: JSONLoader(filepath, jq_schema=".", text_content=True),
            '.csv': lambda: CSVLoader(filepath),
        }
        
        loader_fn = loader_map.get(ext)
        if loader_fn:
            docs = loader_fn().load()
            # Add source metadata
            for doc in docs:
                doc.metadata["source"] = filepath
            # Add to vector store
            self.vector_store.add_documents(docs)
```

### 3.2 Strategy 2: Timestamp-Based

Track last-modified timestamps and re-index files that changed.

```python
import os
from pathlib import Path
from typing import Dict

class TimestampIndexManager:
    def __init__(self):
        self.file_timestamps: Dict[str, float] = {}
    
    def get_file_timestamp(self, filepath: str) -> float:
        return os.path.getmtime(filepath)
    
    def scan_for_changes(self, directory: str) -> tuple:
        """Scan directory and return (added, modified, removed) files."""
        current_timestamps = {}
        for filepath in Path(directory).rglob('*'):
            if filepath.is_file():
                current_timestamps[str(filepath)] = self.get_file_timestamp(str(filepath))
        
        added = set(current_timestamps.keys()) - set(self.file_timestamps.keys())
        removed = set(self.file_timestamps.keys()) - set(current_timestamps.keys())
        modified = {
            f for f in added | removed | set(current_timestamps.keys())
            if f in self.file_timestamps and current_timestamps[f] != self.file_timestamps[f]
        }
        modified -= added  # Remove newly added from modified
        
        self.file_timestamps = current_timestamps
        return added, modified, removed
```

### 3.3 Strategy 3: Directory Snapshot Comparison

Use watchdog's built-in snapshot comparison for polling-based detection.

```python
from watchdog.utils.dirsnapshot import DirectorySnapshot, DirectorySnapshotDiff

class SnapshotIndexManager:
    def __init__(self):
        self.snapshot = None
    
    def take_snapshot(self, path: str) -> DirectorySnapshot:
        return DirectorySnapshot(path=path, recursive=True)
    
    def compare_snapshots(self, snapshot1: DirectorySnapshot, 
                         snapshot2: DirectorySnapshot) -> dict:
        diff = DirectorySnapshotDiff(snapshot1, snapshot2)
        return {
            'added': diff.files_added,
            'removed': diff.files_removed,
            'modified': diff.files_modified,
        }
    
    def scan_incrementally(self, directory: str) -> dict:
        new_snapshot = self.take_snapshot(directory)
        if self.snapshot is None:
            self.snapshot = new_snapshot
            return {'full_scan': True, 'files': list(new_snapshot.paths.keys())}
        
        diff = self.compare_snapshots(self.snapshot, new_snapshot)
        self.snapshot = new_snapshot
        return diff
```

### 3.4 Strategy Comparison

| Strategy | Latency | Complexity | Reliability | Best For |
|----------|---------|------------|-------------|----------|
| Event-Driven | Real-time | Medium | High | Production systems |
| Timestamp | Polling (configurable) | Low | Medium | Simple setups |
| Snapshot | Polling (configurable) | Medium | High | Cross-platform needs |

### 3.5 Recommendation

**Hybrid approach:** Use event-driven (watchfiles) for real-time detection + timestamp verification to handle edge cases (e.g., events missed due to timing).

---

## 4. Configuration-Based Directory Paths

### 4.1 YAML Configuration Structure

Add to `ai_workspace/config/default.yaml`:

```yaml
# Directory scanning configuration
directory_scanning:
  enabled: true
  
  # Directories to monitor
  watched_directories:
    documents: "./data/documents"
    embeddings: "./data/embeddings"
    backups: "./data/backups"
  
  # File extensions to process (case-insensitive)
  allowed_extensions:
    - ".txt"
    - ".md"
    - ".json"
    - ".csv"
    - ".pdf"
    - ".docx"
  
  # Excluded patterns (glob-style)
  excluded_patterns:
    - "__pycache__/*"
    - "*.tmp"
    - "*.swp"
    - ".git/*"
  
  # Scanning settings
  scan:
    recursive: true
    debounce_ms: 500        # Debounce time in milliseconds
    poll_interval_seconds: 60  # Fallback poll interval
    batch_size: 10           # Documents per batch for vector store
  
  # Indexing settings
  indexing:
    chunk_size: 512
    chunk_overlap: 50
    embedding_batch_size: 32
  
  # Persistence
  state:
    file_hashes_db: "./memory/file_hashes.json"
    last_full_scan: "./memory/last_full_scan.json"
```

### 4.2 Loading Configuration in Python

```python
import yaml
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass, field

@dataclass
class DirectoryScanningConfig:
    enabled: bool = True
    watched_directories: dict = field(default_factory=dict)
    allowed_extensions: List[str] = field(default_factory=lambda: [".txt", ".md"])
    excluded_patterns: List[str] = field(default_factory=list)
    scan: dict = field(default_factory=dict)
    indexing: dict = field(default_factory=dict)
    state: dict = field(default_factory=dict)

class ConfigManager:
    def __init__(self, config_dir: str = "./config"):
        self.config_dir = Path(config_dir)
    
    def load_directory_scanning_config(self) -> DirectoryScanningConfig:
        config_path = self.config_dir / "default.yaml"
        
        with open(config_path, 'r') as f:
            config_data = yaml.safe_load(f)
        
        scan_config = config_data.get('directory_scanning', {})
        
        return DirectoryScanningConfig(
            enabled=scan_config.get('enabled', True),
            watched_directories=scan_config.get('watched_directories', {}),
            allowed_extensions=scan_config.get('allowed_extensions', ['.txt', '.md']),
            excluded_patterns=scan_config.get('excluded_patterns', []),
            scan=scan_config.get('scan', {}),
            indexing=scan_config.get('indexing', {}),
            state=scan_config.get('state', {}),
        )
```

---

## 5. File Extension Filtering

### 5.1 Approach 1: pathlib with Case-Insensitive Suffix Check (Recommended)

```python
from pathlib import Path
from typing import List, Set

def is_allowed_extension(filepath: str, allowed_extensions: Set[str]) -> bool:
    """Check if file has an allowed extension (case-insensitive)."""
    ext = Path(filepath).suffix.lower()
    return ext in allowed_extensions

# Usage
ALLOWED_EXTENSIONS = {'.txt', '.md', '.json', '.csv'}
filepath = "./data/Document.TXT"
print(is_allowed_extension(filepath, ALLOWED_EXTENSIONS))  # True
```

### 5.2 Approach 2: glob with Case-Insensitive Pattern

```python
import glob
import fnmatch
import os

def case_insensitive_glob(directory: str, pattern: str) -> List[str]:
    """Glob with case-insensitive matching."""
    all_files = glob.glob(os.path.join(directory, '**', '*'), recursive=True)
    return [
        f for f in all_files
        if os.path.isfile(f) and fnmatch.fnmatch(os.path.basename(f), pattern)
    ]

# Usage - matches .txt, .TXT, .Txt, etc.
txt_files = case_insensitive_glob("./data", "*.txt")
```

### 5.3 Approach 3: Regex Matching

```python
import re
from pathlib import Path

def matches_extension_regex(filepath: str, extensions: List[str]) -> bool:
    """Check if filepath matches any of the allowed extensions."""
    pattern = r'\.(' + '|'.join(ext.lstrip('.').replace('.', r'\.') for ext in extensions) + r')$'
    return bool(re.search(pattern, filepath, re.IGNORECASE))

# Usage
ALLOWED = ['.txt', '.md', '.json', '.csv']
print(matches_extension_regex("./data/file.TXT", ALLOWED))  # True
```

### 5.4 Approach 4: watchfiles Built-in Filter

```python
from pathlib import Path
from watchfiles import awatch

ALLOWED_EXTENSIONS = {'.txt', '.md', '.json', '.csv'}

async def watch_with_filter():
    async for changes in awatch(
        './documents',
        watch_filter=lambda change: (
            Path(change[1]).suffix.lower() in ALLOWED_EXTENSIONS
        ),
    ):
        for change_type, path in changes:
            print(f"[{change_type}] {path}")
```

### 5.5 Recommendation

**Use Approach 1 (pathlib suffix check)** for simplicity and performance. Combine with **Approach 4 (watchfiles filter)** for event-driven scenarios.

---

## 6. Background Worker Patterns

### 6.1 Pattern 1: asyncio Daemon Task (Recommended for FastAPI)

```python
import asyncio
import logging
from typing import Optional
from fastapi import FastAPI
from watchfiles import awatch, Change

logger = logging.getLogger(__name__)

app = FastAPI()

class DirectoryScannerWorker:
    def __init__(self):
        self._task: Optional[asyncio.Task] = None
        self._running = False
    
    async def start(self, watched_dirs: list):
        """Start the background scanning worker."""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._watch_loop(watched_dirs))
        logger.info("Directory scanner worker started")
    
    async def stop(self):
        """Stop the background scanning worker."""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        logger.info("Directory scanner worker stopped")
    
    async def _watch_loop(self, watched_dirs: list):
        """Main watch loop."""
        try:
            async for changes in awatch(*watched_dirs, recursive=True):
                for change_type, path in changes:
                    await self._process_change(change_type, path)
        except asyncio.CancelledError:
            logger.info("Watch loop cancelled")
        except Exception as e:
            logger.error(f"Watch loop error: {e}")
            # Restart after delay
            await asyncio.sleep(5)
            await self._watch_loop(watched_dirs)
    
    async def _process_change(self, change_type: Change, path: str):
        """Process a single file change."""
        if not self._is_relevant_file(path):
            return
        
        if change_type == Change.added:
            logger.info(f"New file detected: {path}")
            await self._index_file(path)
        elif change_type == Change.modified:
            logger.info(f"File modified: {path}")
            await self._reindex_file(path)
        elif change_type == Change.deleted:
            logger.info(f"File deleted: {path}")
            await self._remove_from_index(path)
    
    def _is_relevant_file(self, path: str) -> bool:
        """Check if file should be processed."""
        from pathlib import Path
        allowed = {'.txt', '.md', '.json', '.csv'}
        return Path(path).suffix.lower() in allowed

# Global worker instance
scanner_worker = DirectoryScannerWorker()

@app.on_event("startup")
async def startup_event():
    await scanner_worker.start(["./data/documents"])

@app.on_event("shutdown")
async def shutdown_event():
    await scanner_worker.stop()

@app.get("/health")
async def health():
    return {
        "status": "healthy",
        "scanner_running": scanner_worker._running
    }
```

### 6.2 Pattern 2: FastAPI BackgroundTasks

```python
from fastapi import FastAPI, BackgroundTasks

app = FastAPI()

async def index_document(filepath: str):
    """Background task to index a document."""
    # ... indexing logic ...
    pass

@app.post("/upload")
async def upload_file(file: UploadFile, background_tasks: BackgroundTasks):
    # Save file
    filepath = await save_file(file)
    # Queue indexing as background task
    background_tasks.add_task(index_document, filepath)
    return {"status": "queued", "file": file.filename}
```

**Limitations:** BackgroundTasks runs after response is sent and doesn't persist across requests. Not suitable for continuous monitoring.

### 6.3 Pattern 3: Threading

```python
import threading
from watchdog.observers import Observer

class ThreadedScanner:
    def __init__(self):
        self._observer: Optional[Observer] = None
        self._thread: Optional[threading.Thread] = None
    
    def start(self, path: str):
        event_handler = RAGFileEventHandler()
        self._observer = Observer()
        self._observer.schedule(event_handler, path, recursive=True)
        
        self._thread = threading.Thread(
            target=self._observer.start,
            daemon=True
        )
        self._thread.start()
    
    def stop(self):
        if self._observer:
            self._observer.stop()
            self._observer.join()
```

### 6.4 Pattern 4: Celery (For Distributed Systems)

```python
from celery import Celery

celery = Celery('rag_scanner', broker='redis://localhost:6379/0')

@celery.task
def index_document_task(filepath: str):
    """Celery task for indexing."""
    # ... indexing logic ...
    pass

# Trigger from FastAPI
@app.post("/upload")
async def upload_file(file: UploadFile):
    filepath = await save_file(file)
    index_document_task.delay(filepath)  # Async task
    return {"status": "queued"}
```

### 6.5 Pattern Comparison

| Pattern | Complexity | Scalability | Best For |
|---------|------------|-------------|----------|
| asyncio Daemon | Low | Single-server | FastAPI apps |
| BackgroundTasks | Very Low | Low | Simple one-off tasks |
| Threading | Medium | Single-server | Legacy watchdog |
| Celery | High | Distributed | Large-scale systems |

### 6.6 Recommendation

**For this RAG system: asyncio daemon pattern** (Pattern 1)

Reasons:
1. Native integration with FastAPI lifecycle
2. No external dependencies (Redis, Celery workers)
3. Efficient resource usage
4. Easy to test and debug
5. watchfiles provides the underlying async file watching

---

## 7. ChromaDB/LangChain Integration

### 7.1 ChromaDB Document Management

```python
import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from uuid import uuid4

# Initialize persistent ChromaDB client
client = chromadb.PersistentClient(path="./chroma_db")
collection = client.get_or_create_collection("documents")

# Add documents with unique IDs
def add_documents_to_chroma(documents: list, source_path: str):
    """Add documents to ChromaDB with source tracking."""
    ids = [str(uuid4()) for _ in range(len(documents))]
    
    # Add source metadata for tracking
    for doc, doc_id in zip(documents, ids):
        doc.metadata["source"] = source_path
        doc.metadata["id"] = doc_id
    
    collection.add(
        ids=ids,
        documents=[doc.page_content for doc in documents],
        metadatas=[doc.metadata for doc in documents],
    )

# Update documents (upsert)
def update_document_in_chroma(doc_id: str, new_content: str, new_metadata: dict):
    """Update or insert a document by ID."""
    collection.upsert(
        ids=[doc_id],
        documents=[new_content],
        metadatas=[new_metadata],
    )

# Delete documents by source
def delete_documents_by_source(source_path: str):
    """Delete all documents from a specific source."""
    results = collection.get(
        where={"source": source_path},
        include=["metadatas"]
    )
    if results and results["ids"]:
        collection.delete(ids=results["ids"])
```

### 7.2 LangChain Integration with ChromaDB

```python
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

class RAGIndexManager:
    def __init__(self, embedding_function, persist_dir: str = "./chroma_db"):
        self.embeddings = embedding_function
        self.vector_store = Chroma(
            persist_directory=persist_dir,
            embedding_function=embedding_function,
            collection_name="documents",
        )
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=50,
        )
    
    def index_file(self, filepath: str):
        """Load, split, and index a single file."""
        from langchain.document_loaders import (
            TextLoader, JSONLoader, CSVLoader, UnstructuredMarkdownLoader
        )
        from pathlib import Path
        
        ext = Path(filepath).suffix.lower()
        loader_map = {
            '.txt': lambda: TextLoader(filepath),
            '.md': lambda: UnstructuredMarkdownLoader(filepath),
            '.json': lambda: JSONLoader(filepath, jq_schema=".", text_content=True),
            '.csv': lambda: CSVLoader(filepath),
        }
        
        loader_fn = loader_map.get(ext)
        if not loader_fn:
            raise ValueError(f"Unsupported file type: {ext}")
        
        # Load and split documents
        docs = loader_fn().load()
        split_docs = self.text_splitter.split_documents(docs)
        
        # Add source metadata
        for doc in split_docs:
            doc.metadata["source"] = filepath
        
        # Add to vector store
        self.vector_store.add_documents(split_docs)
        
        return len(split_docs)
    
    def reindex_file(self, filepath: str):
        """Remove old and re-index a file."""
        self.delete_by_source(filepath)
        return self.index_file(filepath)
    
    def delete_by_source(self, filepath: str):
        """Delete all chunks from a specific source file."""
        # ChromaDB doesn't support delete with where clause directly
        # Use get + delete pattern
        results = self.vector_store.get(
            where={"source": filepath},
            include=["metadatas"]
        )
        if results and results["ids"]:
            self.vector_store.delete(ids=results["ids"])
    
    def search(self, query: str, k: int = 5) -> list:
        """Search the vector store."""
        return self.vector_store.similarity_search(query, k=k)
```

### 7.3 Batch Operations for Performance

```python
def batch_index_files(filepaths: list, batch_size: int = 32):
    """Index multiple files in batches for better performance."""
    all_docs = []
    
    for filepath in filepaths:
        docs = load_and_split(filepath)
        for doc in docs:
            doc.metadata["source"] = filepath
        all_docs.extend(docs)
    
    # Add in batches
    for i in range(0, len(all_docs), batch_size):
        batch = all_docs[i:i + batch_size]
        ids = [str(uuid4()) for _ in range(len(batch))]
        vector_store.add_documents(
            documents=batch,
            ids=ids,
        )
```

### 7.4 Persistence and Recovery

```python
import json
from pathlib import Path

class IndexStateManager:
    def __init__(self, state_file: str = "./memory/index_state.json"):
        self.state_file = Path(state_file)
    
    def save_state(self, file_hashes: dict, last_full_scan: str):
        """Save indexing state for recovery."""
        state = {
            "file_hashes": file_hashes,
            "last_full_scan": last_full_scan,
            "timestamp": datetime.now().isoformat(),
        }
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self) -> dict:
        """Load indexing state."""
        if not self.state_file.exists():
            return {}
        with open(self.state_file, 'r') as f:
            return json.load(f)
```

---

## 8. Recommendations

### 8.1 Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                     FastAPI Application                      │
│  ┌──────────────┐  ┌──────────────────┐  ┌───────────────┐ │
│  │   API Routes  │  │  Lifecycle Hooks │  │  Health Check │ │
│  └──────┬───────┘  └────────┬─────────┘  └───────────────┘ │
│         │                   │                                │
│         │                   ▼                                │
│         │         ┌──────────────────┐                      │
│         │         │  DirectoryScanner │                      │
│         │         │  (asyncio daemon) │                      │
│         │         └────────┬─────────┘                      │
│         │                  │  Events                        │
│         │                  ▼                                │
│         │         ┌──────────────────┐                      │
│         │         │ IncrementalIndex │                      │
│         │         │     Manager      │                      │
│         │         └────────┬─────────┘                      │
│         │                  │                                │
│         ▼                  ▼                                │
│  ┌──────────────┐  ┌──────────────────┐                    │
│  │  File Loader  │  │  ChromaDB Store  │                    │
│  │ (LangChain)   │  │  (Persistent)    │                    │
│  └──────────────┘  └──────────────────┘                    │
└─────────────────────────────────────────────────────────────┘
```

### 8.2 Technology Stack

| Component | Recommendation | Reason |
|-----------|---------------|--------|
| File Watching | `watchfiles` | Async, fast, production-proven |
| Document Loading | LangChain `DirectoryLoader` | Flexible, multi-format |
| Vector Store | ChromaDB (PersistentClient) | Already in use, easy API |
| Background Processing | asyncio daemon | Native FastAPI integration |
| Configuration | YAML (`default.yaml`) | Human-readable, already used |
| State Tracking | JSON file + SHA256 hashes | Simple, reliable |

### 8.3 Implementation Priority

1. **Phase 1:** Add YAML configuration for directory paths and extensions
2. **Phase 2:** Implement `DirectoryScannerWorker` with watchfiles
3. **Phase 3:** Add `IncrementalIndexManager` with file hashing
4. **Phase 4:** Integrate with existing ChromaDB via LangChain
5. **Phase 5:** Add state persistence and recovery
6. **Phase 6:** Add tests and monitoring

### 8.4 Key Configuration for `default.yaml`

Add to [`ai_workspace/config/default.yaml`](../config/default.yaml):

```yaml
directory_scanning:
  enabled: true
  watched_directories:
    documents: "./data/documents"
  allowed_extensions:
    - ".txt"
    - ".md"
    - ".json"
    - ".csv"
  scan:
    recursive: true
    debounce_ms: 500
  indexing:
    chunk_size: 512
    chunk_overlap: 50
```

---

## 9. References

1. **Watchdog Library:** [https://pypi.org/project/watchdog/](https://pypi.org/project/watchdog/)
2. **watchfiles Library:** [https://watchfiles.helpmanual.io/](https://watchfiles.helpmanual.io/)
3. **LangChain Chroma Integration:** [https://python.langchain.com/docs/integrations/vectorstores/chroma/](https://python.langchain.com/docs/integrations/vectorstores/chroma/)
4. **LangChain Document Loading:** [https://python.langchain.com/docs/how_to/indexing/](https://python.langchain.com/docs/how_to/indexing/)
5. **FastAPI Background Tasks:** [https://fastapi.tiangolo.com/tutorial/background-tasks/](https://fastapi.tiangolo.com/tutorial/background-tasks/)
6. **ChromaDB Concepts:** [https://cookbook.chromadb.dev/core/concepts/](https://cookbook.chromadb.dev/core/concepts/)
7. **YAML Configuration Patterns:** [https://medium.com/@goelanuj132.in/build-your-own-customizable-rag-pipeline-in-python-with-just-a-yaml-file-71af4e06b2e1](https://medium.com/@goelanuj132.in/build-your-own-customizable-rag-pipeline-in-python-with-just-a-yaml-file-71af4e06b2e1)
8. **Case-Insensitive Glob:** [https://stackoverflow.com/questions/8151300/ignore-case-in-glob-on-linux](https://stackoverflow.com/questions/8151300/ignore-case-in-glob-on-linux)
9. **Incremental RAG Pipeline:** [https://medium.com/codetodeploy/rag-in-production-designing-retrieval-pipelines-that-stay-accurate-as-your-data-changes-90bd3c98f5e1](https://medium.com/codetodeploy/rag-in-production-designing-retrieval-pipelines-that-stay-accurate-as-your-data-changes-90bd3c98f5e1)
10. **FastAPI Background Task Patterns:** [https://betterstack.com/community/guides/scaling-python/background-tasks-in-fastapi/](https://betterstack.com/community/guides/scaling-python/background-tasks-in-fastapi/)
