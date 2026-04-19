# RAG-Project: Повний Огляд Системи

## 1. Що це таке?

Це **локальна RAG-система** (Retrieval-Augmented Generation), побудована для роботи з великими базами знань без необхідності завантажувати весь текст у пам'ять LLM. Вона дозволяє:

- Завантажувати документи (текст, PDF, Markdown тощо)
- Шукати релевантну інформацію за семантичною схожістю
- Отримувати відповіді від локальної LLM на основі знайденого контексту

**Головна мета:** економити RAM/VRAM, використовуючи лише невеликий контекст (2048 токенів) замість завантаження цілих книг.

---

## 2. Архітектура системи

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

---

## 3. Як додати файли для читання RAG-системою

### 3.1 Підтримувані формати

| Формат | Підтримка | Деякі нотатки |
|--------|-----------|---------------|
| `.txt` | ✅ | Простий текст, автоматичне розбиття на чанки |
| `.md` | ✅ | Markdown, зберігає структуру |
| `.pdf` | ⚠️ | Потрібна додаткова обробка (не реалізовано повністю) |
| `.json` | ⚠️ | Через API з метаданими |
| `.csv` | ⚠️ | Через API |
| Зображення | ✅ | CLIP-енкодер для мультимодального пошуку |

### 3.2 Спосіб 1: Через Python API (рекомендовано)

```python
# Приклад додавання документів через MemoryManager
from src.core.memory_manager import MemoryManager, MemoryConfig

config = MemoryConfig(
    persist_directory="./ai_workspace/memory/chroma_db",
    embedding_model="sentence-transformers/all-MiniLM-L6-v2"
)

mm = MemoryManager(config)

# Додавання одного документа
doc_id = mm.add_document(
    content="Текст вашого документа...",
    metadata={"source": "my_file.txt", "type": "text"}
)

# Додавання файлу з диска
with open("./documents/my_document.txt", "r", encoding="utf-8") as f:
    content = f.read()
    doc_id = mm.add_document(content=content, metadata={"source": "my_document.txt"})
```

### 3.3 Спосіб 2: Через HTTP API (FastAPI сервер)

```bash
# Запустіть сервер
cd ai_workspace
python src/api/rag_server.py
```

```bash
# Додайте документ через API
curl -X POST http://localhost:8000/documents \
  -H "Content-Type: application/json" \
  -d '{
    "id": "doc_001",
    "text": "Текст вашого документа українською мовою...",
    "metadata": {"source": "my_file.txt", "category": "docs"}
  }'
```

### 3.4 Спосіб 3: Автоматичне сканування директорії

Створіть скрипт для автоматичного завантаження всіх файлів з папки:

```python
import os
from pathlib import Path
from src.core.memory_manager import MemoryManager, MemoryConfig

def index_directory(directory: str):
    """Індексує всі файли в директорії."""
    config = MemoryConfig()
    mm = MemoryManager(config)
    
    supported_extensions = {'.txt', '.md', '.json', '.csv'}
    
    for root, _, files in os.walk(directory):
        for filename in files:
            ext = Path(filename).suffix.lower()
            if ext not in supported_extensions:
                continue
            
            filepath = os.path.join(root, filename)
            with open(filepath, 'r', encoding='utf-8') as f:
                content = f.read()
            
            metadata = {
                "source": filepath,
                "filename": filename,
                "type": ext.lstrip('.')
            }
            
            doc_id = mm.add_document(content=content, metadata=metadata)
            print(f"Додано: {filepath} (ID: {doc_id})")

# Виклик
index_directory("./documents")
```

---

## 4. Як працює пошук (Retrieval)

### 4.1 Hybrid Search (Гібридний пошук)

Система використовує **два методи одночасно**:

1. **BM25** — ключові слова (точний збіг слів)
2. **Vector Search** — семантична схожість (сенс)

Результати об'єднуються через **Reciprocal Rank Fusion (RRF)**:
- BM25 вага: 0.7 (пріоритет ключовим словам)
- Vector вага: 0.3 (семантичний пошук)
- Результат: ~5.9ms затримка, +18.5% точності vs vector-only

### 4.2 Cross-Encoder Reranker

Після отримання top-k результатів, система пере ранжує їх через:
- Модель: `cross-encoder/ms-marco-MiniLM-L-6-v2`
- Більш точна, але повільніша оцінка релевантності

### 4.3 Graph RAG (опціонально)

Якщо використовується Neo4j:
- Витягуються сутності (PERSON, ORGANIZATION, LOCATION)
- Будується граф зв'язків між документами
- Пошук через обхід графа (depth=2 за замовчуванням)

---

## 5. Як отримати відповідь (Generation)

```python
# Через RAG Agent
from src.agents.rag_agent import RAGAgent

agent = RAGAgent(
    llm_client=llm,
    confidence_threshold=0.8,
    max_iterations=5
)

answer = agent.execute("Яке покарання за статтею 185?")
print(answer)
```

**Процес:**
1. **Reflection** — аналіз запиту, виявлення сутностей
2. **Planning** — створення плану пошуку
3. **Execution** — ітеративний пошук з перевіркою впевненості
4. **Synthesis** — генерація фінальної відповіді

---

## 6. Конфігурація

Основні файли конфігурації:

| Файл | Призначення |
|------|-------------|
| [`config/default.yaml`](../config/default.yaml) | LLM endpoint, chunk_size, top_k |
| [`config/embedding_config.yaml`](../config/embedding_config.yaml) | Налаштування ембедингів |
| [`config/models.yaml`](../config/models.yaml) | Конфігурація моделей |
| [`config/rag_server.yaml`](../config/rag_server.yaml) | Налаштування RAG сервера |
| [`config/services.yaml`](../config/services.yaml) | Сервіси (MCP, LLM, Embeddings) |

**Ключові параметри:**
```yaml
retrieval:
  top_k: 5           # Кількість знайдених документів
  hybrid_search: true # Гібридний пошук увімкнено
  rerank: true        # Reranker увімкнено
  chunk_size: 512     # Розмір чанка (токени)
  chunk_overlap: 50   # Перекриття чанків
```

---

## 7. Запуск системи

### 7.1 Базовий запуск

```bash
cd ai_workspace
./install_deps.sh          # Встановлення залежностей
source .venv/bin/activate  # Активація venv

# Завантаження моделі ембедингів
python -c "from huggingface_hub import snapshot_download; \
  snapshot_download(repo_id='nomic-ai/nomic-embed-text-v1.5', \
  local_dir='./models/embeddings', allow_patterns='*.gguf')"

# Запуск сервера
python src/api/rag_server.py    # FastAPI на :8000
python src/mcp_server.py        # MCP сервер
```

### 7.2 Запуск через оркестратор

```bash
# Запуск всіх сервісів
bash ai_workspace/scripts/core_start.sh

# Зупинка всіх сервісів
bash ai_workspace/scripts/core_stop.sh
```

---

## 8. Структура проекту

```
rag-project/
├── ai_workspace/
│   ├── src/
│   │   ├── api/              # FastAPI сервер
│   │   │   └── rag_server.py # Основний RAG API
│   │   ├── agents/           # Agentic RAG компоненти
│   │   │   ├── rag_agent.py  # RAG Agent з reflection
│   │   │   ├── planner.py    # Планувальник
│   │   │   └── tools.py      # Реєстр інструментів
│   │   ├── core/             # Ядро системи
│   │   │   ├── memory_manager.py     # Керування пам'яттю
│   │   │   ├── service_orchestrator.py # Оркестратор сервісів
│   │   │   ├── retrievers/           # Ретривери
│   │   │   │   ├── hybrid_retriever.py
│   │   │   │   └── bm25_retriever.py
│   │   │   └── rerankers/            # Rerankери
│   │   │       └── cross_encoder_reranker.py
│   │   ├── graph/            # Graph RAG (Neo4j)
│   │   ├── multimodal/       # CLIP для зображень
│   │   ├── security/         # Тенантна ізоляція
│   │   └── mcp_server.py     # MCP сервер
│   ├── config/               # YAML конфігурації
│   ├── docs/                 # Документація
│   ├── memory/               # ChromaDB сховище
│   ├── scripts/              # Скрипти
│   └── tests/                # Тести (309 тестів)
├── README.md
└── requirements.txt
```

---

## 9. Рекомендації для вашого використання

### Для початку:

1. **Створіть папку `documents/`** у корені проекту
2. **Помістіть туди файли** `.txt` або `.md` з вашим контентом
3. **Запустіть індексацію** через скрипт з розділу 3.4
4. **Запустіть RAG сервер** (`python src/api/rag_server.py`)
5. **Надішліть запит** через API або `rag_example.py`

### Оптимізація для української мови:

- Модель `nomic-embed-text-v1.5` підтримує багатомовний пошук
- Для кращих результатів з українською розгляньте `BAAI/bge-m3`
- Використовуйте `chunk_size=512` з `chunk_overlap=50`

### Масштабування:

- Для великих баз: використовуйте **Qdrant** замість ChromaDB
- Для складних зв'язків: увімкніть **Graph RAG** з Neo4j
- Для мультимодального пошуку: використовуйте **CLIP encoder**

---

## 10. Приклад повного workflow

```bash
# 1. Створіть папку для документів
mkdir -p documents

# 2. Додайте файли
echo "Текст першого документа..." > documents/doc1.txt
echo "Текст другого документа..." > documents/doc2.md

# 3. Запустіть індексацію
python -c "
from src.core.memory_manager import MemoryManager, MemoryConfig
import os

config = MemoryConfig(persist_directory='./ai_workspace/memory/chroma_db')
mm = MemoryManager(config)

for f in os.listdir('./documents'):
    with open(f'./documents/{f}', 'r', encoding='utf-8') as file:
        mm.add_document(content=file.read(), metadata={'source': f})
    print(f'Індексовано: {f}')
"

# 4. Запустіть RAG сервер
python src/api/rag_server.py &

# 5. Запитайте щось
curl -X POST http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "model": "shared-rag-v1",
    "messages": [{"role": "user", "content": "Що сказано про...?"}]
  }'
```

---

## 11. Поточний статус проекту

- **Тести:** 293 пройдено, 11 не проходить, 5 пропущено (з 309)
- **Невдалі тести:** TASK-017, TASK-018 (відомі проблеми)
- **Фаза:** Multi-Modal RAG Implementation Complete ✅
- **Блокувачі:** B01 (завантаження моделі ембедингів) — ВИРІШЕНО ✅

---

## 12. Додаткові ресурси

| Документ | Опис |
|----------|------|
| [`docs/HYBRID_SEARCH_METRICS.md`](../docs/HYBRID_SEARCH_METRICS.md) | Метрики гібридного пошуку |
| [`docs/GRAPH_RAG.md`](../docs/GRAPH_RAG.md) | Graph RAG інтеграція |
| [`docs/CLIENT_INTEGRATION_GUIDE.md`](../docs/CLIENT_INTEGRATION_GUIDE.md) | Інтеграція з клієнтами |
| [`PROJECT_STATE.md`](../PROJECT_STATE.md) | Стан проекту |
| [`SETUP_GUIDE.md`](../SETUP_GUIDE.md) | Інструкція з запуску |
