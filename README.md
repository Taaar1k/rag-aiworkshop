# RAG Workbench

<div align="center">

![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=flat-square&logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-RAG_API-009688?style=flat-square&logo=fastapi&logoColor=white)
![ChromaDB](https://img.shields.io/badge/Vector_Store-ChromaDB-5B5BD6?style=flat-square)
![Local First](https://img.shields.io/badge/Local--First-Yes-2ea44f?style=flat-square)

</div>

---

## 1. What this is

A local-first RAG (Retrieval-Augmented Generation) server. It watches a
folder, indexes its files into a ChromaDB vector store, and exposes a
FastAPI endpoint that returns retrieved context plus an LLM-generated
answer. Embeddings and LLM calls go to local OpenAI-compatible servers
(llama.cpp, LM Studio, etc.) — nothing leaves the machine by default.

The server also exposes OpenAI-compatible `/v1/chat/completions` and
`/v1/embeddings`, and ships with a thin FastMCP adapter so MCP clients
can call the same backend.

## 2. Architecture

```text
┌──────────────────────────────────────────────┐
│ CLI: rag                                     │
│   status / start / stop / config / doctor    │
│   workspace selection                        │
│   embedding backend selection                │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│ FastAPI RAG Server :8000                     │
│ src/api/rag_server.py                        │
│                                              │
│ /health, /metrics                            │
│ /scanner/{status,start,stop}                 │
│ /rag/{query,index}                           │
│ /v1/{chat/completions,embeddings}            │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│ Directory Scanner                            │
│ src/core/directory_scanner.py                │
│   reads config/default.yaml                  │
│   extensions: .txt, .md, .json, .csv         │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│ Incremental Index Manager                    │
│ src/core/incremental_index_manager.py        │
│   SHA256 dedup → memory/index_state.json     │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│ ChromaDB Vector Store                        │
│ memory/chroma_db                             │
│ Collection: rag_directory_scanner            │
└───────────────────┬──────────────────────────┘
                    │
┌───────────────────▼──────────────────────────┐
│ Embedding backend                            │
│ default: local OpenAI-compatible API :8090   │
│ alternative: sentence_transformers (in-proc) │
└──────────────────────────────────────────────┘
```

The scanner and `/rag/query` write to and read from the **same ChromaDB
collection** (`rag_directory_scanner`). That shared collection is the
contract between indexer and retriever.

## 3. Prerequisites

- Python 3.10+
- A local OpenAI-compatible **embedding server** on port `8090`
  (typically [llama.cpp](https://github.com/ggml-org/llama.cpp) running
  an embedding model such as `nomic-embed-text-v1.5`).
- A local OpenAI-compatible **LLM server** on port `8080` (any
  llama.cpp-compatible model — choose based on your RAM/VRAM). Optional;
  without it, `/rag/query` returns retrieved context without generation.

`sentence_transformers` is supported as an in-process fallback for
embeddings (no external server required), but loads a model into memory
on startup.

## 4. Installation

```bash
git clone https://github.com/Taaar1k/rag-aiworkshop.git
cd rag-aiworkshop

python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Pull the embedding model (used by both the local API server and the
`sentence_transformers` fallback):

```python
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="nomic-ai/nomic-embed-text-v1.5",
    local_dir="./models/embeddings",
)
```

Install the `rag` shell function:

```bash
cd scripts
./install_rag_cli.sh install
source ~/.zshrc   # or ~/.bashrc
```

The installer adds an `RAG_ROOT` export and a `rag()` function to your
shell rc. After this, `rag` works from any directory.

## 5. Quick Start

```bash
# 1. Tell the scanner which folder to watch
rag -w ~/notes

# 2. Start the API on :8000
rag start

# 3. Confirm the scanner picked up files
curl -s http://localhost:8000/scanner/status | python3 -m json.tool

# 4. Query
curl -s -X POST http://localhost:8000/rag/query \
  -H "Content-Type: application/json" \
  -d '{"query":"summarize my notes about X","top_k":5}' \
  | python3 -m json.tool
```

If `/rag/query` returns `sources: []`, see [Troubleshooting](#10-troubleshooting).

## 6. CLI Reference

| Command | Purpose |
|---|---|
| `rag -h` | Show all commands |
| `rag status` | Check embedding (`:8090`) and LLM (`:8080`) servers |
| `rag test` | Generate a test embedding to verify the embedding backend |
| `rag config` | Print resolved configuration |
| `rag start` | Start FastAPI server on `:8000` |
| `rag stop` | Stop the FastAPI server (`pkill -f uvicorn`) |
| `rag doctor` | Smoke-test: workspace, scanner, API, env vars |
| `rag -w` | Show watched folder |
| `rag -w PATH` | Set watched folder (rewrites `config/default.yaml`) |
| `rag -l` | Set `EMBEDDING_SOURCE=local_api` (in `.env`) |
| `rag -st` | Set `EMBEDDING_SOURCE=sentence_transformers` |

After changing `config/default.yaml` (manually or via `rag -w`), restart
the server — config is loaded once at startup.

## 7. API Reference

| Method | Path | Purpose |
|---|---|---|
| `GET` | `/health` | Lightweight cached health check |
| `GET` | `/health/verbose` | Full health check (no cache) |
| `GET` | `/metrics` | Server metrics |
| `GET` | `/rate-limit-status` | Current rate-limit budget for the caller |
| `GET` | `/scanner/status` | Scanner state |
| `POST` | `/scanner/start` | Start scanner |
| `POST` | `/scanner/stop` | Stop scanner |
| `POST` | `/rag/query` | Retrieve + generate. Body: `{query, top_k, filters?, temperature?, max_tokens?}` |
| `POST` | `/rag/index` | Add a document directly. Body: `{id, text, metadata?}` |
| `POST` | `/v1/chat/completions` | OpenAI-compatible chat |
| `POST` | `/v1/embeddings` | OpenAI-compatible embeddings |

Rate limiting is enabled by default (`slowapi`, in-memory). Limits are
configured in `config/default.yaml::rate_limiting` and via
`RATE_LIMIT_*` env vars.

CORS is env-driven: `CORS_ORIGINS` (comma-separated).

## 8. Configuration

### `config/default.yaml`

Key fields:

```yaml
llm:
  endpoint: http://localhost:8080/v1/chat/completions
  timeout: 30
  max_tokens: 2048

retrieval:
  top_k: 5
  hybrid_search: true
  rerank: true
  chunk_size: 512
  chunk_overlap: 50

server:
  host: 0.0.0.0
  port: 8000

directory_scanning:
  enabled: true
  watched_directories:
    - path: "/path/to/your/notes"
      recursive: true
  allowed_extensions:
    - .txt
    - .md
    - .json
    - .csv
```

### `.env`

Common variables (see `.env.example` for the full list):

```text
EMBEDDING_SOURCE=local_api          # or sentence_transformers
EMBEDDING_ENDPOINT=http://localhost:8090/v1/embeddings
LLM_ENDPOINT=http://localhost:8080/v1/chat/completions
CORS_ORIGINS=http://localhost:3000,http://localhost:5173
RATE_LIMIT_ANONYMOUS="100 per minute"
RATE_LIMIT_AUTHENTICATED="1000 per minute"
```

`rag -l` and `rag -st` rewrite `EMBEDDING_SOURCE` in this file.

## 9. MCP Integration

`src/mcp_server.py` is a [FastMCP](https://github.com/jlowin/fastmcp)
server that proxies tool calls to the FastAPI RAG API over HTTP. It does
not maintain its own index.

Tools exposed:

| Tool | Backed by |
|---|---|
| `search` | `POST /rag/query` |
| `ask` | `POST /rag/query` |
| `add_document` | `POST /rag/index` |
| `list_documents` | reads `memory/index_state.json` |
| `health_check` | `GET /health` + `GET /scanner/status` |

Example MCP client config:

```json
{
  "command": "/path/to/rag-aiworkshop/venv/bin/python",
  "args": ["src/mcp_server.py"],
  "cwd": "/path/to/rag-aiworkshop",
  "env": {
    "PYTHONPATH": ".",
    "PYTHONIOENCODING": "utf-8",
    "RAG_API_BASE_URL": "http://localhost:8000"
  }
}
```

`RAG_API_BASE_URL` defaults to `http://localhost:8000`. The FastAPI
server must be running for MCP tools to work.

## 10. Testing

`pytest.ini` excludes integration tests by default
(`addopts = -m "not integration"`).

```bash
# (run from repo root)
.venv/bin/python -m pytest tests/                                # unit tests
.venv/bin/python -m pytest tests/test_scanner_integration.py -v  # one file
.venv/bin/python -m pytest -m integration                        # opt-in
.venv/bin/python -m pytest -m optional                           # CLIP/PIL deps
```

### Troubleshooting

**`/rag/query` returns `sources: []`** — check that the scanner has
indexed something:

```bash
curl -s http://localhost:8000/scanner/status | python3 -m json.tool
python3 -m json.tool memory/index_state.json
```

Common causes: watched folder is empty, files don't match
`allowed_extensions`, embedding server is down (`rag status`).

**Config change didn't take effect** — config is read at startup. Run
`rag stop && rag start`.

**`rag -w PATH` doesn't pass arguments** — ensure the shell function
uses `"${@:-status}"`. Reinstall via `install_rag_cli.sh install` and
`source` your shell rc.

## 11. Status

### Active

- Directory scanner with SHA256 deduplication
- ChromaDB-backed `/rag/query` and `/rag/index`
- OpenAI-compatible `/v1/chat/completions` and `/v1/embeddings`
- Hybrid search (BM25 + vector) with cross-encoder reranker
- Rate limiting, CORS whitelist, structured health checks
- FastMCP adapter

### Experimental modules (present in `src/` but not wired into the server)

These are kept in-tree for ongoing work; the FastAPI server does not
import them today:

- `src/agents/` — RAG agent with reflection pattern (planner, tools,
  collaboration)
- `src/graph/` — Graph RAG with Neo4j (entity extraction, hybrid graph
  retrieval)
- `src/multimodal/` — CLIP-based image encoder, unified text+image
  retriever
- `src/security/` — JWT-based tenant isolation, row-level security,
  audit log

Tests for these live under `tests/` and run independently.

## 12. License

MIT — see [LICENSE](LICENSE).
