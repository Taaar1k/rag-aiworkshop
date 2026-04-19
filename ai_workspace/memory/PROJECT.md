# PROJECT: RAG MCP Server with llama.cpp

## Goal
Create a modern MCP RAG server using FastMCP, LangChain, and ChromaDB for working with local documents using Llama-3.

## Current Status
- **Status**: Preparing for refactoring
- **Progress**: 25% (1 of 4 stages)
- **Session ID**: (not used - stateless architecture)
- **Active Mode**: default

## Master Checklist
- [x] Project structure created
- [x] Dependencies installed
- [x] Basic RAG example created
- [x] Launch instructions created
- [x] **TASK-001**: Define first task (completed)
- [x] **TASK-003**: Embedding model config created (completed)
- [ ] **TASK-002**: Refactoring for FastMCP (in progress)
- [ ] **TASK-004**: Rebuild general memory system (pending)
- [ ] **TASK-005**: Integration and testing of new architecture (pending)
- [ ] Download embedding model nomic-embed-text-v1.5.Q4_K_M.gguf
- [ ] Create FastMCP server
- [ ] Integrate LangChain and ChromaDB
- [ ] Test and implement

## Project Structure
```
ai_workspace/
├── config/
│   ├── default.yaml      # Configuration
│   └── models.yaml       # Model maps
├── models/
│   ├── llm/
│   │   └── Llama-3-8B-Instruct-Q4_K_M.gguf  ✅ (available)
│   └── embeddings/       ❌ (needs to be downloaded)
├── scripts/
│   └── rag_example.py    # Basic example
├── src/
│   └── core/
│       └── config.py     # Settings
├── memory/
│   ├── PROJECT.md        # This file
│   ├── TASKS/
│   │   ├── INDEX.md
│   │   ├── TASK-001.md
│   │   └── TASK-002.md
│   └── ROLES/
├── venv/                 # Virtual environment
├── download_embedding_model.py
├── SETUP_GUIDE.md
├── spec.md
└── requirements.txt
```

## Technical Stack
- **Framework**: FastMCP (MCP servers)
- **Orchestration**: LangChain (RAG pipeline)
- **Vector Store**: ChromaDB (persistent storage)
- **LLM**: Llama-3-8B-Instruct (llama.cpp)
- **Embeddings**: nomic-embed-text-v1.5 (needs to be downloaded)

## Roles
- **PM**: Project Manager - planning and coordination
- **Dev**: Developer - code implementation
- **Thinker**: Analyst - architectural decisions
- **Scout**: Researcher - solution search
- **Scribe**: Technical Writer - documentation

## Notes
- The project uses stateless architecture (Session ID not needed)
- Virtual environment venv already created in parent directory
- Need to download embedding model before testing
- MCP server does not require session state saving

## Next Steps
1. Download embedding model nomic-embed-text-v1.5.Q4_K_M.gguf
2. Implement FastMCP server with tools
3. Integrate LangChain and ChromaDB
4. Test RAG pipeline
5. Rebuild general memory system
6. Configure embedding model settings
