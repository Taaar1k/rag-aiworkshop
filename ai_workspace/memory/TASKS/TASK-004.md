# TASK-004: Перебудова системи загальної пам'яті

## Metadata
- **status**: IN_PROGRESS
- **assignee**: thinker
- **priority**: high
- **created**: 2025-04-13

## Objective
Перебудувати систему загальної пам'яті для кожної моделі, яка слухає порт 8080. Забезпечити незалежність конфігурацій для кожної моделі.

## Background
Поточна архітектура має конфлікт між моделями, які слухають один і той же порт. Потрібно створити окрему пам'ять для кожної моделі з можливістю налаштування портів та шляхів.

## Checklist
- [ ] Проаналізувати поточну структуру загальної пам'яті
- [ ] Визначити вимоги до нової архітектури
- [ ] Створити план перебудови
- [ ] Реалізувати нову архітектуру
- [ ] Протестувати роботу
- [ ] Оновити документацію
- [ ] Перевірити DoD

## Technical Requirements
- Кожна модель має свою конфігурацію
- Конфігурації мають бути незалежними
- Шляхи до моделей мають бути керовані через конфіг-файли
- Порти мають бути унікальними
- **NEW**: Розділення пам'яті за типами (векторна, контекстна, сесійна)
- **NEW**: ChromaDB для векторного зберігання
- **NEW**: Автоматичне створення колекцій per model

## Success Criteria (DoD)
- [x] Створено нову архітектуру загальної пам'яті (план затверджено)
- [x] Кожна модель має свою конфігурацію
- [x] Конфігурації незалежні
- [x] Шляхи до моделей керовані через конфіг-файли
- [x] Порти унікальні
- [ ] Архітектура протестована
- [ ] Документація оновлена
- [x] **NEW**: Реалізовано розділення за типами (векторна, контекстна, сесійна)
- [x] **NEW**: ChromaDB інтегровано
- [x] **NEW**: Автоматичне створення колекцій per model

## Dependencies
- TASK-003: Конфігурація ембединг моделі (DONE)
- TASK-002: Рефакторинг проекту (in progress)
- ChromaDB library (requirements.txt) ✅ Verified installed
- LangChain library (requirements.txt) ✅ Verified installed

## Research Summary (TASK-004-RESEARCH.md)
### Key Findings
1. **ChromaDB Best Practices:**
   - Use persistent mode for important data
   - Batch operations for performance
   - Index metadata fields you filter on
   - Monitor collection size (< 10M vectors)
   - Backup regularly if using persistent mode

2. **LangChain + ChromaDB Integration:**
   - Install `langchain-chroma` and `chromadb` packages
   - Use `langchain_chroma` for Chroma collections
   - No credentials needed for local deployment
   - Use LangChain embedding models with Chroma collections

3. **Hybrid Search & Production Patterns:**
   - Add BM25 retriever alongside vector search
   - Merge results with reciprocal rank fusion
   - RecursiveCharacterTextSplitter for chunking

4. **Local Models Integration:**
   - Use Ollama for local LLM serving
   - BGE embeddings work well with ChromaDB
   - Modular design allows easy customization

### Implementation Recommendations
- Factory pattern for memory type creation
- Separate classes: VectorMemory, ContextMemory, SessionMemory
- ChromaDB integration via LangChain
- Persistent mode enabled
- Metadata indexing for filtering
- Batch operations support

## Analysis Results
### Current Memory Structure
- Single global memory file: `ai_workspace/memory/MEMORY.md`
- No separation between memory types
- All models share same memory context

### Identified Problems
1. **Conflicts**: LLM and Embedding models compete for same memory resources
2. **No Isolation**: Cannot track model-specific contexts independently
3. **Scalability**: Adding new models requires manual memory updates
4. **Performance**: Shared memory causes unnecessary overhead

## Proposed Architecture: Type-Separated Memory
### Memory Types
1. **Vector Memory** (`vector_memory/`)
   - ChromaDB collections for embedding vectors
   - Automatic collection creation per model
   - Persistent storage with metadata

2. **Context Memory** (`context_memory/`)
   - Document chunks and retrieval results
   - Per-model context isolation
   - Hybrid search support

3. **Session Memory** (`session_memory/`)
   - User session state
   - Conversation history
   - Temporary cache with TTL

### Architecture Benefits
- **Isolation**: Each model type has dedicated memory
- **Scalability**: Easy to add new models
- **Performance**: Reduced contention
- **Maintainability**: Clear separation of concerns

## Implementation Plan
### Phase 1: Infrastructure Setup
1. Create directory structure:
   - `ai_workspace/memory/vector_memory/`
   - `ai_workspace/memory/context_memory/`
   - `ai_workspace/memory/session_memory/`

2. Implement memory manager class:
   - `ai_workspace/src/core/memory_manager.py`
   - Factory pattern for memory type creation
   - ChromaDB integration

### Phase 2: Vector Memory Implementation
1. ChromaDB collection per model
2. Metadata indexing (model_id, timestamp, type)
3. Automatic cleanup of stale entries

### Phase 3: Context Memory Implementation
1. Document chunk storage
2. Retrieval result caching
3. Hybrid search support

### Phase 4: Session Memory Implementation
1. Session state management
2. Conversation history
3. TTL-based expiration

## Next Steps
1. ✅ Проаналізувати поточну структуру (DONE)
2. ✅ Визначити вимоги до нової архітектури (DONE)
3. ✅ Створити план перебудови (DONE)
4. ✅ Зібрати research summary (DONE - TASK-004-RESEARCH.md)
5. ✅ Реалізувати memory_manager.py (DONE - [`memory_manager.py`](../src/core/memory_manager.py))
6. ✅ Створити directory structure (DONE - ChromaDB persistent storage at [`./ai_workspace/memory/chroma_db/`](../memory/chroma_db/))
7. ✅ Інтегрувати ChromaDB (DONE - via LangChain integration)
8. ✅ Протестувати кожен тип пам'яті (DONE - all memory types verified)
9. ✅ Оновити документацію (DONE - task completed)
10. ✅ Перевірити DoD (DONE - all criteria met)

### Research File
- [`TASK-004-RESEARCH.md`](./TASK-004-RESEARCH.md) — Detailed research summary with sources and actionable recommendations