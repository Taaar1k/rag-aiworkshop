# CORE RAG Workbench

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-RAG_API-009688?style=flat-square&logo=fastapi&logoColor=white)
![ChromaDB](https://img.shields.io/badge/Vector_Store-ChromaDB-5B5BD6?style=flat-square)
![MCP](https://img.shields.io/badge/MCP-Pi_Ready-6963ff?style=flat-square)
![Local First](https://img.shields.io/badge/Local--First-Yes-2ea44f?style=flat-square)

**Local-first RAG workspace for Pi, CORE notes, and agent memory.**

</div>

---

## Overview

CORE RAG Workbench is a local RAG system built around a watched workspace folder, automatic file scanning, ChromaDB vector storage, and a FastAPI query endpoint. It is currently wired for the working local setup used by Pi: the scanner indexes files from a selected folder, `/rag/query` searches the same ChromaDB collection, and the CLI provides short commands for status, workspace selection, and embedding backend switching.

The current working path is:

```text
/home/tarik/CORE
```

The active API query path is:

```text
POST http://localhost:8000/rag/query
```

---

## Current Working Architecture

```text
┌──────────────────────────────────────────────┐
│ CLI: rag                                     │
│ - status / start / stop                      │
│ - workspace selection                        │
│ - embedding backend selection                │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│ FastAPI RAG Server :8000                     │
│ src/api/rag_server.py                        │
│                                              │
│ Endpoints:                                   │
│ - /health                                    │
│ - /scanner/status                            │
│ - /scanner/start                             │
│ - /scanner/stop                              │
│ - /rag/query                                 │
│ - /rag/index                                 │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│ Directory Scanner                            │
│ src/core/directory_scanner.py                │
│                                              │
│ Reads config/default.yaml                    │
│ Watches: /home/tarik/CORE                    │
│ Extensions: .txt, .md, .json, .csv           │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│ Incremental Index Manager                    │
│ src/core/incremental_index_manager.py        │
│                                              │
│ Tracks file hashes in:                       │
│ ai_workspace/memory/index_state.json         │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│ ChromaDB Vector Store                        │
│ ai_workspace/memory/chroma_db                │
│                                              │
│ Active collection:                           │
│ rag_directory_scanner                        │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│ Embeddings                                   │
│ Default: local API                           │
│ http://localhost:8090/v1/embeddings          │
│                                              │
│ Alternative: sentence_transformers           │
└──────────────────────────────────────────────┘
```

---

## What Works Now

- CLI command `rag` is installed through shell function.
- `rag -w` shows or changes the watched folder.
- The watched folder is stored in `ai_workspace/config/default.yaml`.
- Scanner indexes files into ChromaDB.
- `/rag/query` searches the same ChromaDB collection used by the scanner.
- `/rag/index` writes into the same ChromaDB backend.
- Qdrant is no longer required for the normal scanner → query flow.
- Pi MCP can run the local RAG MCP server from `ai_workspace/src/mcp_server.py`.

---

## Repository Layout

```text
rag-project/
├── README.md
├── ai_workspace/
│   ├── config/
│   │   ├── default.yaml              # Main working config: watched folder, scanner, retrieval
│   │   ├── embedding_config.yaml     # Embedding server settings
│   │   ├── models.yaml               # Model path aliases
│   │   ├── rag_server.yaml           # Legacy / extended RAG server settings
│   │   ├── services.yaml             # Service orchestration config
│   │   └── memory_persistence.yaml   # Session persistence config
│   ├── src/
│   │   ├── api/
│   │   │   ├── rag_server.py         # FastAPI server and /rag/query
│   │   │   └── scanner_manager.py    # Scanner lifecycle endpoints
│   │   ├── core/
│   │   │   ├── directory_scanner.py
│   │   │   ├── incremental_index_manager.py
│   │   │   ├── memory_manager.py
│   │   │   ├── service_orchestrator.py
│   │   │   ├── retrievers/
│   │   │   └── rerankers/
│   │   ├── agents/
│   │   ├── evaluation/
│   │   ├── graph/
│   │   ├── multimodal/
│   │   ├── security/
│   │   ├── shared_rag/
│   │   └── mcp_server.py             # FastMCP server for Pi/MCP clients
│   ├── scripts/
│   │   ├── rag_cli.py                # Main CLI implementation
│   │   ├── install_rag_cli.sh        # Shell installer for rag function
│   │   ├── core_start.sh
│   │   ├── core_stop.sh
│   │   └── start_rag_server.py
│   ├── memory/
│   │   ├── chroma_db/                # ChromaDB persistent store
│   │   └── index_state.json          # Scanner hash state
│   ├── docs/
│   ├── tests/
│   └── .env
└── venv/
```

---

## CLI Commands

Use `rag -h` to print the current command list.

```bash
rag -h
```

Current commands:

```bash
rag status
rag test
rag config
rag start
rag stop
rag -w
rag -w /path/to/folder
rag -l
rag -st
```

### Command Reference

| Command | Purpose |
|---|---|
| `rag -h` | Show CLI help and command list |
| `rag status` | Check embedding server, LLM server, and Qdrant status |
| `rag test` | Test embedding generation |
| `rag config` | Show selected RAG configuration details |
| `rag start` | Start FastAPI RAG server on port `8000` |
| `rag stop` | Stop the RAG server process |
| `rag -w` | Show current watched workspace folder |
| `rag -w /path/to/folder` | Set watched workspace folder in `config/default.yaml` |
| `rag -l` | Set `EMBEDDING_SOURCE=local_api` |
| `rag -st` | Set `EMBEDDING_SOURCE=sentence_transformers` |

---

## Quick Start

### 1. Install the CLI function

```bash
cd /home/tarik/Sandbox/my-plugin/rag-project/ai_workspace/scripts
./install_rag_cli.sh install
source ~/.zshrc
```

The installer adds this shell function:

```bash
export RAG_ROOT="/home/tarik/Sandbox/my-plugin/rag-project/ai_workspace"

rag() {
    cd "$RAG_ROOT" && python scripts/rag_cli.py "${@:-status}"
}
```

### 2. Check the watched folder

```bash
rag -w
```

Expected current value:

```text
/home/tarik/CORE
```

### 3. Change the watched folder

```bash
rag -w /home/tarik/CORE
```

This updates:

```text
/home/tarik/Sandbox/my-plugin/rag-project/ai_workspace/config/default.yaml
```

under:

```yaml
directory_scanning:
  watched_directories:
    - path: "/home/tarik/CORE"
      recursive: true
```

### 4. Start or restart the API

```bash
rag stop
rag start
```

The server starts at:

```text
http://localhost:8000
```

### 5. Check scanner status

```bash
curl -s http://localhost:8000/scanner/status | python3 -m json.tool
```

Expected shape:

```json
{
  "scanner_running": true,
  "scanner_enabled": true,
  "watched_directories": 1
}
```

### 6. Query the RAG API

```bash
curl -s -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query":"checkin progress goals CORE","top_k":10}' \
  | python3 -m json.tool
```

Successful response includes non-empty `sources`, for example:

```json
{
  "sources": [
    {
      "source": "/home/tarik/CORE/goals.md",
      "filename": "goals.md"
    }
  ]
}
```

---

## Configuration

### Main Config

```text
ai_workspace/config/default.yaml
```

Important fields:

```yaml
llm:
  endpoint: "http://localhost:8080/v1/chat/completions"

retrieval:
  top_k: 5
  hybrid_search: true
  rerank: true
  chunk_size: 512
  chunk_overlap: 50

server:
  host: "0.0.0.0"
  port: 8000

directory_scanning:
  enabled: true
  watched_directories:
    - path: "/home/tarik/CORE"
      recursive: true
  allowed_extensions:
    - ".txt"
    - ".md"
    - ".json"
    - ".csv"
```

### Embedding Config

```text
ai_workspace/config/embedding_config.yaml
```

Default local endpoint:

```text
http://localhost:8090/v1/embeddings
```

Switch backend:

```bash
rag -l   # local_api
rag -st  # sentence_transformers
```

This edits `.env`:

```text
EMBEDDING_SOURCE=local_api
```

or:

```text
EMBEDDING_SOURCE=sentence_transformers
```

---

## API Endpoints

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | System health |
| `GET` | `/health/verbose` | Detailed health |
| `GET` | `/scanner/status` | Scanner status |
| `POST` | `/scanner/start` | Start scanner |
| `POST` | `/scanner/stop` | Stop scanner |
| `POST` | `/rag/query` | Search indexed files and generate answer |
| `POST` | `/rag/index` | Add a document directly into ChromaDB |
| `POST` | `/v1/chat/completions` | OpenAI-compatible chat endpoint |
| `POST` | `/v1/embeddings` | OpenAI-compatible embeddings endpoint |

---

## RAG Query Flow

Current `/rag/query` behavior:

1. Receives query JSON.
2. Generates query embedding through the configured embedding backend.
3. Opens ChromaDB persistent store:

   ```text
   ./ai_workspace/memory/chroma_db
   ```

4. Searches collection:

   ```text
   rag_directory_scanner
   ```

5. Builds context from returned documents.
6. Uses LLM if available; otherwise returns a fallback answer with retrieved context.
7. Returns `answer`, `sources`, and `metadata`.

Example request:

```bash
curl -s -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{
    "query": "What are my current CORE goals?",
    "top_k": 5
  }'
```

---

## Direct Indexing

You can add a document directly without placing it in the watched folder:

```bash
curl -s -X POST http://localhost:8000/rag/index \
  -H "Content-Type: application/json" \
  -d '{
    "id": "manual-doc-001",
    "text": "This is a manual document for CORE RAG.",
    "metadata": {
      "source": "manual",
      "tag": "test"
    }
  }'
```

This writes into the same ChromaDB collection used by the scanner.

---

## Scanner Behavior

The scanner watches files with these extensions:

```text
.txt
.md
.json
.csv
```

It tracks indexed files by SHA256 hash in:

```text
ai_workspace/memory/index_state.json
```

To force a fresh scan after changing the workspace:

```bash
curl -s -X POST http://localhost:8000/scanner/stop | python3 -m json.tool
curl -s -X POST http://localhost:8000/scanner/start | python3 -m json.tool
```

If the API server was already running before a config change, restart it:

```bash
rag stop
rag start
```

---

## MCP / Pi Integration

Pi uses the RAG MCP server from:

```text
/home/tarik/Sandbox/my-plugin/rag-project/ai_workspace/src/mcp_server.py
```

The MCP server is intentionally a thin adapter over the FastAPI RAG API. It does not maintain a separate ChromaDB index or document list.

Current flow:

```text
Pi MCP tool → src/mcp_server.py → http://localhost:8000/rag/query → ChromaDB rag_directory_scanner
```

Typical Pi MCP server config points to:

```json
{
  "command": "/home/tarik/Sandbox/my-plugin/rag-project/venv/bin/python",
  "args": ["src/mcp_server.py"],
  "cwd": "/home/tarik/Sandbox/my-plugin/rag-project/ai_workspace",
  "env": {
    "PYTHONPATH": ".",
    "PYTHONIOENCODING": "utf-8",
    "RAG_API_BASE_URL": "http://localhost:8000"
  }
}
```

Available MCP tools from the RAG adapter:

```text
search          → POST /rag/query
ask             → POST /rag/query
add_document    → POST /rag/index
list_documents  → scanner index_state.json
health_check    → GET /health + GET /scanner/status
```

After editing MCP server code, reload Pi or reconnect the MCP server so direct tools use the new process.

---

## Testing

Run tests from `ai_workspace`:

```bash
cd /home/tarik/Sandbox/my-plugin/rag-project/ai_workspace
.venv/bin/python -m pytest tests/
```

Run selected tests:

```bash
.venv/bin/python -m pytest tests/test_scanner_integration.py -v
.venv/bin/python -m pytest tests/test_memory_persistence.py -v
.venv/bin/python -m pytest tests/test_hybrid_retriever.py -v
```

Some tests may require optional services or models. Treat integration tests separately from quick unit checks.

---

## Operational Notes

- Normal RAG API search no longer depends on Qdrant.
- Qdrant-related code remains in the project as legacy/optional infrastructure.
- The active vector store for scanned files is ChromaDB.
- If `sources` is empty after changing workspace:
  1. Check `rag -w`.
  2. Confirm files exist and have supported extensions.
  3. Restart API: `rag stop && rag start`.
  4. Check scanner status.
  5. Inspect `ai_workspace/memory/index_state.json`.
- If using `sentence_transformers`, GPU memory may be required. The local API backend is the safer default.

---

## Troubleshooting

### `rag -w /path` changes config but query returns old files

Restart the API server so it reloads `config/default.yaml`:

```bash
rag stop
rag start
```

### Scanner shows running but no files indexed

Check supported files:

```bash
find "$(python scripts/rag_cli.py -w 2>/dev/null)" -type f \
  \( -name '*.txt' -o -name '*.md' -o -name '*.json' -o -name '*.csv' \)
```

Or inspect state:

```bash
python3 -m json.tool ai_workspace/memory/index_state.json
```

### `/rag/query` returns `sources: []`

Check whether ChromaDB has indexed documents and whether the embedding server is running:

```bash
rag status
curl -s http://localhost:8000/scanner/status | python3 -m json.tool
```

### `rag` function does not pass arguments

Make sure shell function uses `"${@:-status}"`, not only `$1`:

```bash
rag() {
    cd "$RAG_ROOT" && python scripts/rag_cli.py "${@:-status}"
}
```

Then reload shell:

```bash
source ~/.zshrc
```

---

## License

MIT — see [LICENSE](LICENSE).
