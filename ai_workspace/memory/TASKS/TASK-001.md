# TASK-001: Ініціалізація проекту RAG з llama.cpp

## Metadata
- status: DONE
- assignee: PM_MASTER
- created: 2025-04-13
- completed: 2025-04-13
- priority: HIGH

## Objective
Створити базову структуру проекту для локального RAG-системи з використанням llama.cpp, визначити архітектуру та підготувати умови для подальшої розробки.

## Background
Розробка локальної RAG-системи з підтримкою української мови вимагає чіткої архітектури та підготовленої інфраструктури.

## Scope
- ✅ Створення структури папок
- ✅ Ініціалізація PROJECT_STATE.md
- ✅ Створення TASK_BOARD.md
- ✅ Визначення архітектури
- ✅ Ідентифікація залежностей

## Constraints
- Використання локальних моделей
- Підтримка української мови
- Економія RAM/VRAM
- llama.cpp як основа

## Assumptions
- Python venv буде створено
- Моделі llama.cpp будуть завантажені
- Доступ до GPU/CPU ресурсів є

## Options Considered
- Використання ChromaDB vs in-memory векторного зберігання
- FastMCP vs класичний API
- Вибір між різними моделями ембедингів

## Decision and Rationale
Обрано: ChromaDB для персистентного зберігання, FastMCP для сервера, nomic-embed-text-v1.5 для ембедингів.

## Plan / Execution Steps
1. Створити структуру папок
2. Створити PROJECT_STATE.md
3. Створити TASK_BOARD.md
4. Визначити архітектуру
5. Ідентифікувати залежності

## Risks and Mitigations
- Ризик: Недостатньо пам'яті — Мітігація: Використання quantized моделей
- Ризик: Повільна генерація — Мітігація: Оптимізація n_ctx, n_gpu_layers

## Dependencies
- Встановлений Python
- Доступ до GPU/VRAM
- Моделі llama.cpp (Llama-3-8B, nomic-embed-text)

## Success Criteria (DoD)
- [x] Структура папок створено
- [x] PROJECT_STATE.md створено та заповнено
- [x] TASK_BOARD.md створено
- [x] Архітектура визначено
- [x] Залежності ідентифіковано
- [x] BLOCKER B01 (модель ембедингів) визначено

## Open Questions
- Який порт використовувати для сервера?
- Яка стратегія chunking документів?

## Change Log
- 2025-04-13: Створено TASK-001
- 2025-04-13: Оновлено статус на DONE
- 2025-04-13: Додано метадані, DoD, ризики, залежності 
