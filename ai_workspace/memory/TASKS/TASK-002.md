# TASK-002: Project refactoring for modern RAG MCP stack

## Metadata
- status: in_progress
- assignee: dev
- priority: high
- created: 2025-04-13
- last_updated: 2026-04-13

## Objective
Transition project to modern MCP RAG server architecture using FastMCP, LangChain, and ChromaDB to improve scalability and performance.

## Background
Analysis of modern RAG MCP servers showed that best practices include:
- FastMCP for server creation
- LangChain for RAG pipeline orchestration
- ChromaDB for vector storage
- llama.cpp for local generation

## Current Configuration
- **LLM Model**: Qwen3.5-35B-A3B-APEX-Compact.gguf (port 8080)
- **Embedding Model**: nomic-embed-text-v1.5.Q4_K_M.gguf (port 8090)
- **RAG System**: Built-in RAG system with llama.cpp

## Checklist
- [x] **Analysis** - Review current architecture
- [x] **Analysis** - Identify strengths
- [x] **Design** - Create FastMCP server architecture
- [x] **Design** - Define MCP tools
- [x] **Design** - Plan ChromaDB migration
- [x] **Implement** - Implement FastMCP server
- [x] **Implement** - Integrate with LangChain
- [x] **Implement** - Configure ChromaDB
- [x] **Test** - Test all tools
- [ ] **Test** - Validate RAG pipeline
- [ ] **Document** - Update documentation
- [ ] **Deploy** - Deploy to production

## Technical Requirements
- FastMCP >= 1.0.0
- LangChain >= 0.1.0
- ChromaDB >= 0.4.0
- llama-cpp-python >= 0.2.0

## Success Criteria
- ✅ MCP server works through FastMCP
- ✅ search() and ask() tools function
- ✅ ChromaDB stores vectors persistently
- ✅ LLM Qwen3.5 generates responses
- ✅ Response time < 2 seconds

## Dependencies
- TASK-001: Визначення першої задачі (виконано)
- Модель nomic-embed-text-v1.5.Q4_K_M.gguf (завантажена, порт 8090)
- Модель Qwen3.5-35B-A3B-APEX-Compact.gguf (завантажена, порт 8080)

## Notes
- Обидві моделі завантажені та працюють
- RAG система готова до використання
- Потрібно реалізувати FastMCP сервер

## Next Steps
1. ✅ Створити FastMCP сервер - [`ai_workspace/src/mcp_server.py`](ai_workspace/src/mcp_server.py)
2. ✅ Реалізувати інструменти MCP (search, ask, add_document, list_documents, health_check)
3. ✅ Інтегрувати LangChain та ChromaDB
4. ⏳ Тестувати та впроваджувати
