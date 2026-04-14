import numpy as np
import requests
import json
from sklearn.metrics.pairwise import cosine_similarity
from llama_cpp import Llama

# 1. НАЛАШТУВАННЯ: Адреса сервера ембедингів (запущеного через llama.cpp на порті 8090)
EMBEDDING_API_URL = "http://127.0.0.1:8090/v1/embeddings"
MODEL_NAME = "nomic-embed-text-v1.5"

# Функція для отримання ембедингу через HTTP-запит до llama.cpp сервера
def get_embedding(text):
    response = requests.post(
        EMBEDDING_API_URL,
        headers={"Content-Type": "application/json"},
        json={
            "input": text,
            "model": MODEL_NAME
        }
    )
    if response.status_code != 200:
        raise Exception(f"Embedding API error: {response.status_code} - {response.text}")
    return response.json()['data'][0]['embedding']

# 2. Завантажуємо локальну LLM через llama.cpp
# Вибираємо модель, яка у вас є (наприклад Llama-3-8B-Instruct-Q4_K_M.gguf)
print("Завантаження LLM (llama.cpp)...")
llm = Llama(
    model_path="./models/Llama-3-8B-Instruct-Q4_K_M.gguf", 
    n_ctx=2048, # ЕКОНОМІЯ: Нам потрібен контекст всього 2048, бо ми використовуємо RAG!
    n_gpu_layers=-1 # Якщо є відеокарта
)

# 3. Наш великий текст (для прикладу - масив абзаців/фрагментів)
documents = [
    "Компанія LlamaCorp була заснована у 2021 році в місті Київ.",
    "Головний продукт компанії - це інструменти для оптимізації штучного інтелекту.",
    "Дохід компанії у 2023 році склав 5 мільйонів доларів.",
    "Llama.cpp написаний на C/C++ розробником Georgi Gerganov.",
    "RAG дозволяє економити контекстне вікно моделі."
]

# 4. Створюємо вектори (ембединги) для наших документів
print("Векторизація документів...")
doc_embeddings = [get_embedding(doc) for doc in documents]

def rag_query(user_query, top_k=2):
    # А) Векторизуємо запит користувача
    query_embedding = get_embedding(user_query)
    
    # Б) Шукаємо схожість між запитом та документами (Косинусна схожість)
    similarities = cosine_similarity([query_embedding], doc_embeddings)[0]
    
    # В) Беремо індекси top_k найбільш схожих шматків
    top_indices = np.argsort(similarities)[-top_k:][::-1]
    
    # Г) Формуємо знайдений контекст
    retrieved_context = "\n".join([documents[i] for i in top_indices])
    
    # Д) Створюємо промпт для llama.cpp
    # ВАЖЛИВО: Жорстко вказуємо моделі використовувати ТІЛЬКИ контекст!
    prompt = f"""<|system|>
Ти корисний асистент. Дай відповідь на питання користувача, використовуючи ТІЛЬКИ наданий контекст. 
Якщо в контексті немає відповіді, так і скажи: \"Я не знаю\"

КОНТЕКСТ:
{retrieved_context}
<|user|>
{user_query}
<|assistant|>
"""
    
    print(f"\n--- Знайдений контекст ---\n{retrieved_context}\n--------------------------")
    
    # Е) Генеруємо відповідь через llama.cpp
    output = llm(
        prompt,
        max_tokens=256,
        temperature=0.1, # Низька температура, щоб модель не фантазувала
        stop=["<|user|>"]
    )
    
    return output['choices'][0]['text'].strip()

# ТЕСТУЄМО
query = "Який дохід мала компанія LlamaCorp і де вона заснована?"
print("\nЗапит:", query)
answer = rag_query(query)
print("\nВідповідь моделі:", answer)