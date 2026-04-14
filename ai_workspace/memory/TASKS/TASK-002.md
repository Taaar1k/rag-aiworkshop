# TASK-002: Рефакторинг проекту під сучасний RAG MCP стек

## Metadata
- status: in_progress
- assignee: dev
- priority: high
- created: 2025-04-13
- last_updated: 2026-04-13

## Objective
Перехід проекту на сучасну архітектуру MCP RAG сервера з використанням FastMCP, LangChain та ChromaDB для покращення масштабованості та продуктивності.

## Background
Аналіз сучасних RAG MCP серверів показав, що найкращі практики включають:
- FastMCP для створення серверів
- LangChain для оркестрації RAG pipeline
- ChromaDB для векторного зберігання
- llama.cpp для локальної генерації

## Current Configuration
- **LLM Model**: Qwen3.5-35B-A3B-APEX-Compact.gguf (порт 8080)
- **Embedding Model**: nomic-embed-text-v1.5.Q4_K_M.gguf (порт 8090)
- **RAG System**: Вбудована система RAG з llama.cpp

## Checklist
- [x] **Analysis** - Огляд поточної архітектури
- [x] **Analysis** - Визначення міцних точок
- [x] **Design** - Створення архітектури FastMCP сервера
- [x] **Design** - Визначення інструментів MCP
- [x] **Design** - Планування міграції на ChromaDB
- [x] **Implement** - Реалізація FastMCP сервера
- [x] **Implement** - Інтеграція з LangChain
- [x] **Implement** - Налаштування ChromaDB
- [x] **Test** - Тестування всіх інструментів
- [ ] **Test** - Валидація RAG pipeline
- [ ] **Document** - Оновлення документації
- [ ] **Deploy** - Впровадження в продакшн

## Technical Requirements
- FastMCP >= 1.0.0
- LangChain >= 0.1.0
- ChromaDB >= 0.4.0
- llama-cpp-python >= 0.2.0

## Success Criteria
- ✅ MCP сервер працює через FastMCP
- ✅ Інструменти search() та ask() функціонують
- ✅ ChromaDB зберігає вектори персистентно
- ✅ LLM Qwen3.5 генерує відповіді
- ✅ Час відповіді < 2 секунди

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
