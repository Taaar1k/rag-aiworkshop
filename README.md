# rag-workshop

**A local-first RAG system built autonomously by a multi-agent framework.**

This repository is the reference implementation produced by the [C.E.H. multi-agent framework](https://workshopai2.gumroad.com/l/ceh-framework) — a prompt-based agent cluster (PM, Code, Scaut, Ask, Debug, Writer, Healer) that ships production-grade code with evidence-gated task execution.

Every feature below was planned, implemented, tested, and verified by agents following a 13-section task discipline with Definition-of-Done gates. Task files and evidence bundles live in [`ai_workspace/memory/TASKS/`](./ai_workspace/memory/TASKS/) — **the real audit trail, unedited**.

---

## What's Inside

- **Hybrid search** — BM25 + dense vectors fused via Reciprocal Rank Fusion (+18.5% accuracy vs vector-only, ~5.9ms latency). See [`ai_workspace/docs/HYBRID_SEARCH_METRICS.md`](./ai_workspace/docs/HYBRID_SEARCH_METRICS.md).
- **Cross-encoder reranker** — `cross-encoder/ms-marco-MiniLM-L-6-v2` over top-k results.
- **Evaluation framework** — MRR, NDCG, baseline reports in [`ai_workspace/evaluation_results/`](./ai_workspace/evaluation_results/).
- **Agentic RAG** — self-critique loop with query rewriting.
- **Tenant isolation** — per-tenant filtering, audit logging, Bearer-token auth ([`src/security/`](./ai_workspace/src/security/)).
- **Multi-modal** — CLIP-based image encoder, unified embedding space, text↔image cross-modal search.
- **Graph RAG** — Neo4j integration with entity extraction and graph traversal ([`ai_workspace/docs/GRAPH_RAG.md`](./ai_workspace/docs/GRAPH_RAG.md)).
- **MCP server** — exposes the RAG pipeline to any MCP-compatible client.

---

## Tech Stack

- **LLM**: Llama-3-8B-Instruct (Q4_K_M GGUF) via `llama-cpp-python`
- **Embeddings**: `nomic-embed-text-v1.5` (768-dim, multilingual-friendly)
- **Vector store**: ChromaDB / Qdrant (configurable)
- **Keyword search**: BM25 (`rank-bm25`)
- **Reranker**: sentence-transformers cross-encoder
- **API**: FastAPI with OpenAI-compatible `/v1/chat/completions`
- **Framework**: LangChain core

---

## Quick Start

```bash
git clone https://github.com/<your-user>/rag-workshop.git
cd rag-workshop/ai_workspace
./install_deps.sh
```

Download the embedding model:

```bash
python -c "from huggingface_hub import snapshot_download; \
  snapshot_download(repo_id='nomic-ai/nomic-embed-text-v1.5', \
  local_dir='./models/embeddings', allow_patterns='*.gguf')"
```

Start the llama.cpp servers (embeddings on 8090, LLM on 8080) and run:

```bash
source .venv/bin/activate
python src/mcp_server.py
```

Full setup walkthrough: [`ai_workspace/INSTRUCTIONS.md`](./ai_workspace/INSTRUCTIONS.md).

---

## Testing

```bash
# Unit tests (excludes integration tests marked with @pytest.mark.integration)
cd ai_workspace
.venv/bin/python -m pytest tests/

# Integration tests (require running llama.cpp + API services)
.venv/bin/python -m pytest tests/ -m integration
```

**Current state (2026-04-16)**: 293 passed · 11 failing · 5 skipped out of 309.
The 11 failures are tracked as [TASK-017, TASK-018](./ai_workspace/memory/TASKS/) and are being resolved by the C.E.H. agent cluster itself — see the task board for live status.
Integration tests (3 tests in `test_rag_server.py`) have been marked with `@pytest.mark.integration` and excluded from default runs via [`ai_workspace/pytest.ini`](./ai_workspace/pytest.ini).

---

## Project Layout

```
rag-workshop/
├── ai_workspace/
│   ├── src/
│   │   ├── api/              # FastAPI RAG server
│   │   ├── agents/           # Agentic RAG components
│   │   ├── core/             # Retrievers, rerankers, memory
│   │   ├── evaluation/       # MRR / NDCG framework
│   │   ├── graph/            # Graph RAG (Neo4j)
│   │   ├── multimodal/       # CLIP image pipeline
│   │   ├── security/         # Tenant isolation + audit
│   │   └── mcp_server.py
│   ├── tests/                # 309 tests, ~95% passing
│   ├── config/               # YAML configs
│   ├── docs/                 # Feature deep-dives
│   ├── evaluation_results/   # Baseline metrics (evidence)
│   ├── memory/
│   │   └── TASKS/            # Every task that built this repo
│   └── PROJECT_STATE.md      # PM-owned state file
├── README.md                 # this file
└── LICENSE                   # MIT
```

---

## How This Was Built

Each feature corresponds to a numbered task:

| Task | What | Status |
|---|---|---|
| TASK-007 | Hybrid Search (BM25 + vectors, RRF fusion) | DONE |
| TASK-008 | Cross-Encoder Reranker | DONE |
| TASK-009 | Evaluation Framework (MRR/NDCG) | DONE |
| TASK-010 | Agentic RAG patterns | DONE |
| TASK-011 | Tenant Isolation + audit logging | DONE |
| TASK-012 | Multi-Modal (CLIP) | DONE |
| TASK-013 | Graph RAG (Neo4j) | DONE |
| TASK-017 | Fix HybridRetriever API mismatch in stress tests | TODO |
| TASK-018 | Fix Tenant API integration test route lookup | TODO |
| TASK-019 | Mark llama.cpp-dependent tests as `integration` | TODO |

Each task file in [`ai_workspace/memory/TASKS/`](./ai_workspace/memory/TASKS/) includes the objective, DoD checklist, evidence, and change log. This is what "evidence-gated autonomous development" actually looks like in practice — nothing hidden, nothing polished post-hoc.

---

## Get the Framework

This repo proves the framework works. If you want the framework itself — the 7 agents, templates, system registry, and custom modes — it's available as a prompt pack:

**[C.E.H. Multi-Agent Framework on Gumroad](https://workshopai2.gumroad.com/l/ceh-framework)**

- $29 Starter: full framework, 7 agents, all templates
- $49 Pro: Starter + detailed setup + this project as an example
- $99/hr Setup Service: I configure C.E.H. for your stack

---

## License

MIT — see [LICENSE](./LICENSE).

---

*Built with [C.E.H.](https://workshopai2.gumroad.com/l/ceh-framework) — the multi-agent framework that ships code with evidence.*
