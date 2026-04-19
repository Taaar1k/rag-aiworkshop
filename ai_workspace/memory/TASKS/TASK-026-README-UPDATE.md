# TASK-026: README.md Update — Full System Documentation

## 1. Metadata
- Task ID: TASK-026
- Created: 2026-04-19
- Assigned to: Writer
- Mode: light
- Status: TODO
- Priority: P1
- Related: Root README.md at [`README.md`](../../README.md)

## 2. Context

The root [`README.md`](../../README.md) was written during early project development and no longer reflects the current state of the system. The project has evolved significantly since then — new features were added, architecture changed, tests improved, and configuration became more flexible.

This task requires the Writer agent to:
1. Analyze the current system state
2. Compare with the old README.md
3. Create updated, comprehensive documentation

## 3. System Evolution Summary

### 3.1 What It Was (Initial State — TASK-001, April 2025)

**Original Goals:**
- Local RAG system based on llama.cpp
- Ukrainian language support via multilingual embeddings
- RAM/VRAM savings through RAG approach

**Initial Architecture:**
- Single global memory file (`memory/MEMORY.md`) — no separation between memory types
- All models shared the same memory context
- In-memory vector storage (numpy) — no persistence
- Basic FastAPI server on port 8000
- Simple vector search only (no hybrid)
- Hardcoded model paths in source code

**Initial Tech Stack:**
- LLM: Llama-3-8B-Instruct via llama-cpp-python
- Embeddings: nomic-embed-text-v1.5 (discovered later)
- Vector DB: in-memory numpy arrays
- No reranker, no graph RAG, no multimodal support

**What Was Missing:**
- No BM25/keyword search
- No cross-encoder reranker
- No evaluation framework
- No tenant isolation/security
- No multimodal (image) support
- No Graph RAG (Neo4j)
- No MCP server
- No directory scanning/auto-indexing
- No environment variable configuration
- No proper test organization (integration tests mixed with unit tests)

### 3.2 What It Is Now (Current State — April 2026)

**Current Architecture:**
```
┌─────────────────────────────────────────────────────────────┐
│                      КЛІЄНТ (API)                          │
│   FastAPI сервер (:8000) | MCP сервер | OpenAI-сумісні     │
└────────────────────────┬────────────────────────────────────┘
                          │
┌────────────────────────▼────────────────────────────────────┐
│                    RAG ORCHESTRATOR                         │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────┐  │
│  │ Hybrid       │  │ Cross-Encoder│  │ Graph RAG        │  │
│  │ Retriever    │  │ Reranker     │  │ (Neo4j)          │  │
│  │ (BM25+Vector)│  │              │  │                  │  │
│  └──────┬───────┘  └──────┬───────┘  └────────┬─────────┘  │
└─────────┼─────────────────┼────────────────────┼────────────┘
          │                 │                    │
┌─────────▼─────────────────▼────────────────────▼────────────┐
│                    MEMORY LAYER                             │
│  ┌──────────────────┐  ┌─────────────────────────────────┐  │
│  │ ChromaDB         │  │ Qdrant (опціонально)            │  │
│  │ (векторне сховище)│  │                                 │  │
│  └──────────────────┘  └─────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
          │
┌─────────▼────────────────────────────────────────────────────┐
│                   EMBEDDING + LLM                           │
│  ┌──────────────────────┐  ┌──────────────────────────────┐  │
│  │ nomic-embed-text     │  │ Llama-3-8B / Qwen3-35B       │  │
│  │ v1.5 (768-dim)       │  │ через llama.cpp (:8080)      │  │
│  │ на порту :8090       │  │                              │  │
│  └──────────────────────┘  └──────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

**Current Features (All Implemented via Tasks):**

| Task | Feature | Status | Key Details |
|------|---------|--------|-------------|
| TASK-007 | Hybrid Search (BM25 + Vector) | DONE | RRF fusion, +18.5% accuracy, ~5.9ms latency |
| TASK-008 | Cross-Encoder Reranker | DONE | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| TASK-009 | Evaluation Framework | DONE | MRR, NDCG, baseline reports |
| TASK-010 | Agentic RAG | DONE | Self-critique loop, query rewriting |
| TASK-011 | Tenant Isolation | DONE | Per-tenant filtering, audit logging, Bearer-token auth |
| TASK-012 | Multi-Modal (CLIP) | DONE | Image encoder, unified embedding space, cross-modal search |
| TASK-013 | Graph RAG (Neo4j) | DONE | Entity extraction, graph traversal, hybrid graph+vector |
| TASK-019 | Test Organization | DONE | Integration tests marked with `@pytest.mark.integration` |
| TASK-023 | Environment Variables | DONE | All hardcoded paths replaced with `os.getenv()` |
| TASK-024 | Integration Test Fixes | DONE | 7 passed, 1 skipped, 0 failed |
| TASK-025 | Directory Scanning | PENDING | Auto-indexing with `watchfiles`, incremental updates |

**Current Tech Stack:**
- **LLM**: Llama-3-8B-Instruct (Q4_K_M GGUF) via `llama-cpp-python` — configurable via env vars
- **Embeddings**: `nomic-embed-text-v1.5` (768-dim, multilingual)
- **Vector Store**: ChromaDB (persistent) / Qdrant (optional)
- **Keyword Search**: BM25 (`rank-bm25`)
- **Reranker**: sentence-transformers cross-encoder
- **Graph DB**: Neo4j (optional)
- **Image Encoder**: CLIP-vit-base-patch32
- **API**: FastAPI with OpenAI-compatible `/v1/chat/completions`
- **MCP Server**: FastMCP for agent integration
- **Framework**: LangChain core

**Current Test Status:**
- 293 passed · 11 failing · 5 skipped out of 309
- Integration tests properly separated via `@pytest.mark.integration`
- pytest.ini configured for default unit test runs

**Configuration System:**
- YAML configs: `default.yaml`, `embedding_config.yaml`, `models.yaml`, `rag_server.yaml`, `services.yaml`
- Environment variables: `.env.example` with 9+ configurable parameters
- Directory scanning config in `default.yaml`

### 3.3 What Was Improved and Why

| Improvement | Why | Task |
|-------------|-----|------|
| Hybrid Search (BM25 + Vector) | Vector-only search loses technical terms and specific keywords; RRF fusion adds +18.5% accuracy | TASK-007 |
| Cross-Encoder Reranker | Top-k results need re-ranking for better relevance; cross-encoder provides deeper semantic analysis | TASK-008 |
| Evaluation Framework | Need measurable metrics (MRR, NDCG) to track improvements and compare approaches | TASK-009 |
| Agentic RAG | Self-critique loop enables query rewriting and iterative refinement for complex queries | TASK-010 |
| Tenant Isolation | Multi-tenant deployments need data separation, audit trails, and authentication | TASK-011 |
| Multi-Modal Support | Documents often contain images; cross-modal search enables text↔image retrieval | TASK-012 |
| Graph RAG | Relationship-heavy domains (legal, healthcare, finance) benefit from graph-based context | TASK-013 |
| Test Organization | llama.cpp-dependent tests were polluting CI output; integration tests need separate execution | TASK-019 |
| Environment Variables | Hardcoded paths prevented model switching without code changes | TASK-023 |
| Integration Test Fixes | Tests were failing due to improper mocking; fixes ensure reliable CI | TASK-024 |
| Directory Scanning (pending) | Manual document indexing is error-prone; auto-indexing with file watching improves UX | TASK-025 |

## 4. Old README.md Analysis

### Current README.md Content (What Needs Updating):

**Sections that are outdated:**
1. **Tech Stack** — Missing: reranker, Graph RAG, MCP, multimodal, tenant isolation
2. **Quick Start** — Missing: directory scanning, environment variables, service orchestrator
3. **Testing** — Test count outdated (was 293/309, may have changed)
4. **Project Layout** — Missing: `evaluation/`, `security/`, `multimodal/`, `graph/` directories
5. **How This Was Built** — Task table incomplete (missing TASK-019, TASK-023, TASK-024)
6. **Missing sections**: No Graph RAG docs link, no multimodal docs, no client integration guide

**Sections that are still accurate:**
- Project description and purpose
- Hybrid search mention (but needs updated metrics)
- Evaluation framework mention
- Agentic RAG mention
- License section

### Documentation Files Available for Reference:
| File | Purpose |
|------|---------|
| [`ai_workspace/docs/HYBRID_SEARCH_METRICS.md`](ai_workspace/docs/HYBRID_SEARCH_METRICS.md) | Hybrid search performance metrics |
| [`ai_workspace/docs/GRAPH_RAG.md`](ai_workspace/docs/GRAPH_RAG.md) | Graph RAG integration guide |
| [`ai_workspace/docs/CLIENT_INTEGRATION_GUIDE.md`](ai_workspace/docs/CLIENT_INTEGRATION_GUIDE.md) | Client SDK integration |
| [`ai_workspace/docs/DIRECTORY_SCANNING.md`](ai_workspace/docs/DIRECTORY_SCANNING.md) | Directory scanning feature |
| [`ai_workspace/docs/UKRAINIAN_OVERVIEW.md`](ai_workspace/docs/UKRAINIAN_OVERVIEW.md) | Full system overview in Ukrainian |
| [`ai_workspace/docs/DIRECTORY_SCANNING_RESEARCH.md`](ai_workspace/docs/DIRECTORY_SCANNING_RESEARCH.md) | Research behind directory scanning |
| [`ai_workspace/INSTRUCTIONS.md`](ai_workspace/INSTRUCTIONS.md) | Setup and launch instructions |
| [`ai_workspace/memory/PROJECT_STATE.md`](ai_workspace/memory/PROJECT_STATE.md) | PM-owned project state |

## 5. Deliverables

The Writer agent should produce an **updated README.md** that includes:

1. **Project Title & Description** — Keep the multi-agent framework context
2. **What's Inside** — Updated feature table with ALL current features
3. **Tech Stack** — Complete tech stack with all components
4. **Architecture Diagram** — ASCII architecture from Ukrainian overview
5. **Quick Start** — Updated setup instructions with env vars, directory scanning
6. **Configuration** — Environment variables reference table
7. **Features Deep-Dive** — Links to all doc files
8. **Testing** — Current test status and commands
9. **Project Layout** — Updated directory tree
10. **How This Was Built** — Complete task table with all tasks
11. **API Usage** — Quick API examples
12. **License** — Keep as-is

## 6. Writing Guidelines

- Keep the professional, evidence-gated development narrative
- Update all metrics (test counts, accuracy improvements, latency)
- Include architecture diagram from Ukrainian overview
- Link to all documentation files
- Keep the framework promotion section at the end
- Use markdown formatting consistently
- Ensure all file paths in links are correct relative to root

## 7. DoD (Definition of Done)

- [ ] DoD-1: README.md includes ALL current features (hybrid search, reranker, Graph RAG, multimodal, tenant isolation, MCP)
- [ ] DoD-2: Architecture diagram included and accurate
- [ ] DoD-3: Tech stack complete with all components
- [ ] DoD-4: Quick Start section updated with env vars and directory scanning
- [ ] DoD-5: Configuration section with environment variables table
- [ ] DoD-6: All documentation links valid and pointing to correct files
- [ ] DoD-7: Task table complete with all tasks (TASK-007 through TASK-025)
- [ ] DoD-8: Test section reflects current status
- [ ] DoD-9: Project layout includes all directories
- [ ] DoD-10: No broken markdown links

## 8. Evidence Requirements

Before marking DONE, provide:
- Readable diff of changes made to README.md
- List of all sections updated
- Verification that all markdown links resolve correctly

## 9. Change Log

- 2026-04-19: Created by PM — comprehensive system analysis provided
