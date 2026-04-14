# PROJECT: RAG MCP Server з llama.cpp

## Goal
Створити сучасний MCP RAG сервер з використанням FastMCP, LangChain та ChromaDB для роботи з локальними документами за допомогою Llama-3.

## Current Status
- **Статус**: Підготовка до рефакторингу
- **Прогрес**: 25% (1 з 4 етапів)
- **Session ID**: (не використовується - stateless архітектура)
- **Active Mode**: default

## Master Checklist
- [x] Створено структуру проекту
- [x] Встановлено залежності
- [x] Створено базовий приклад RAG
- [x] Створено інструкції з запуску
- [x] **TASK-001**: Визначити першу задачу (виконано)
- [x] **TASK-003**: Створено конфіг ембединг моделі (completed)
- [ ] **TASK-002**: Рефакторинг під FastMCP (in progress)
- [ ] **TASK-004**: Перебудова системи загальної пам'яті (pending)
- [ ] **TASK-005**: Інтеграція та тестування нової архітектури (pending)
- [ ] Завантажити модель ембедингів nomic-embed-text-v1.5.Q4_K_M.gguf
- [ ] Створити FastMCP сервер
- [ ] Інтегрувати LangChain та ChromaDB
- [ ] Тестувати та впроваджувати

## Project Structure
```
ai_workspace/
├── config/
│   ├── default.yaml      # Конфігурація
│   └── models.yaml       # Мапи моделей
├── models/
│   ├── llm/
│   │   └── Llama-3-8B-Instruct-Q4_K_M.gguf  ✅ (наявна)
│   └── embeddings/       ❌ (потрібно завантажити)
├── scripts/
│   └── rag_example.py    # Базовий приклад
├── src/
│   └── core/
│       └── config.py     # Налаштування
├── memory/
│   ├── PROJECT.md        # Цей файл
│   ├── TASKS/
│   │   ├── INDEX.md
│   │   ├── TASK-001.md
│   │   └── TASK-002.md
│   └── ROLES/
├── venv/                 # Віртуальне середовище
├── download_embedding_model.py
├── INSTRUCTIONS.md
├── spec.md
└── requirements.txt
```

## Technical Stack
- **Framework**: FastMCP (MCP сервери)
- **Orchestration**: LangChain (RAG pipeline)
- **Vector Store**: ChromaDB (персистентне зберігання)
- **LLM**: Llama-3-8B-Instruct (llama.cpp)
- **Embeddings**: nomic-embed-text-v1.5 (потрібно завантажити)

## Roles
- **PM**: Project Manager - планування та координація
- **Dev**: Developer - реалізація коду
- **Thinker**: Аналітик - архітектурні рішення
- **Scout**: Дослідник - пошук рішень
- **Scribe**: Технічний письменник - документація

## Notes
- Проект використовує stateless архітектуру (Session ID не потрібен)
- Віртуальне середовище venv вже створено в батьківській директорії
- Потрібно завантажити модель ембедингів перед тестуванням
- MCP сервер не потребує збереження стану сесії

## Next Steps
1. Завантажити модель nomic-embed-text-v1.5.Q4_K_M.gguf
2. Реалізувати FastMCP сервер з інструментами
3. Інтегрувати LangChain та ChromaDB
4. Протестувати RAG pipeline
5. Перебудувати систему загальної пам'яті
6. Налаштувати конфігурацію ембединг моделі
