# RAG з llama.cpp - ІНСТРУКЦІЯ З ЗАПУСКУ

## Поточний стан
✅ Структура проекту створена
✅ LLM модель `Llama-3-8B-Instruct-Q4_K_M.gguf` завантажена
✅ Конфігурація та приклади готові
✅ Залежності встановлені
❌ Модель ембедингів відсутня

## ⚠️ Arch Linux / Externally-Managed Environment

If you see `error: externally-managed-environment`, use the automated installer:

```bash
cd <repo-root>/ai_workspace
./install_deps.sh
```

This script creates a proper virtual environment and installs all dependencies.

## Необхідні кроки

### 1. Встановлення залежностей (Alternative Method)
If you prefer manual installation:

```bash
cd <repo-root>/ai_workspace
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements_mcp.txt
```

### 2. Завантаження моделі ембедингів

Оскільки файл `nomic-embed-text-v1.5.Q4_K_M.gguf` відсутній, вам потрібно завантажити його.

#### Спосіб 1: Через Python скрипт
```bash
cd <repo-root>/ai_workspace
source .venv/bin/activate
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='nomic-ai/nomic-embed-text-v1.5', local_dir='./models/embeddings', allow_patterns='*.gguf')"
```

#### Спосіб 2: Через `huggingface-cli` (рекомендовано)
```bash
# Встановіть CLI якщо ще не встановлено
pip install huggingface_hub

# Або завантажте через Python API
python -c "from huggingface_hub import snapshot_download; snapshot_download(repo_id='nomic-ai/nomic-embed-text-v1.5', local_dir='./models/embeddings', allow_patterns='*.gguf')"
```

#### Спосіб 3: Ручне завантаження
1. Перейдіть на https://huggingface.co/nomic-ai/nomic-embed-text-v1.5
2. Знайдіть файл `nomic-embed-text-v1.5.Q4_K_M.gguf`
3. Завантажте його у папку `./models/embeddings/`

### 3. Запуск прикладу RAG

```bash
cd <repo-root>/ai_workspace
source .venv/bin/activate
python scripts/rag_example.py
```

### 4. Запуск сервера для ембедингів (опціонально)

Якщо ви хочете використовувати HTTP API для ембедингів:

```bash
# Запустіть сервер llama.cpp на порту 8090
./llama-server --model ./models/embeddings/nomic-embed-text-v1.5.Q4_K_M.gguf --port 8090
```

### 5. Перевірка роботи

Після запуску `rag_example.py` ви повинні побачити:
1. Повідомлення про завантаження LLM
2. Векторизацію документів
3. Виведення знайденого контексту
4. Відповідь моделі на запит

## Тестові запити

Спробуйте наступні запити після запуску:
- "Який дохід мала компанія LlamaCorp?"
- "Де заснована компанія LlamaCorp?"
- "Що є головним продуктом компанії?"
- "Хто написав Llama.cpp?"

## Проблеми та вирішення

**Проблема: "ModuleNotFoundError: No module named 'llama_cpp'"**
Рішення: Переконайтесь, що активували віртуальне середовище:
```bash
source .venv/bin/activate
```

**Проблема: "Model file not found"**
Рішення: Перевірте шлях до файлу моделі у конфігурації та переконайтесь що файл існує.

**Проблема: "CUDA out of memory"**
Рішення: Зменшіть `n_ctx` або зніміть `n_gpu_layers=-1` для використання CPU.

## Подальші кроки

1. Інтегруйте з реальною базою документів
2. Додайте веб-інтерфейс (FastAPI + React/Vue)
3. Реалізуйте кешування ембедингів
4. Додайте підтримку різних форматів документів
