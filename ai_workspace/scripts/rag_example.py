import os
import numpy as np
import requests
import json
from sklearn.metrics.pairwise import cosine_similarity
from llama_cpp import Llama

# 1. SETUP: Embedding server address (running via llama.cpp on port 8090)
EMBEDDING_API_URL = os.getenv("EMBEDDING_ENDPOINT", "http://127.0.0.1:8090/v1/embeddings")
MODEL_NAME = "nomic-embed-text-v1.5"

# Function to get embedding via HTTP request to llama.cpp server
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

# 2. Load local LLM via llama.cpp
# Choose the model you have (e.g. Llama-3-8B-Instruct-Q4_K_M.gguf)
print("Loading LLM (llama.cpp)...")
llm = Llama(
    model_path="./models/Llama-3-8B-Instruct-Q4_K_M.gguf", 
    n_ctx=2048, # ECONOMY: We need only 2048 context, because we use RAG!
    n_gpu_layers=-1 # If you have a GPU
)

# 3. Our large text (for example - array of paragraphs/chunks)
documents = [
    "LlamaCorp company was founded in 2021 in Kyiv.",
    "The company's main product is tools for artificial intelligence optimization.",
    "The company's revenue in 2023 was 5 million dollars.",
    "Llama.cpp is written in C/C++ by developer Georgi Gerganov.",
    "RAG allows saving the model's context window."
]

# 4. Create vectors (embeddings) for our documents
print("Vectorizing documents...")
doc_embeddings = [get_embedding(doc) for doc in documents]

def rag_query(user_query, top_k=2):
    # A) Vectorize user query
    query_embedding = get_embedding(user_query)
    
    # B) Search similarity between query and documents (Cosine similarity)
    similarities = cosine_similarity([query_embedding], doc_embeddings)[0]
    
    # C) Take indices of top_k most similar chunks
    top_indices = np.argsort(similarities)[-top_k:][::-1]
    
    # D) Form found context
    retrieved_context = "\n".join([documents[i] for i in top_indices])
    
    # E) Create prompt for llama.cpp
    # IMPORTANT: Strictly tell the model to use ONLY the context!
    prompt = f"""<|system|>
You are a helpful assistant. Answer the user's question using ONLY the provided context. 
If there is no answer in the context, say so: "I don't know"

CONTEXT:
{retrieved_context}
<|user|>
{user_query}
<|assistant|>
"""
    
    print(f"\n--- Found context ---\n{retrieved_context}\n--------------------------")
    
    # F) Generate response via llama.cpp
    output = llm(
        prompt,
        max_tokens=256,
        temperature=0.1, # Low temperature so the model doesn't hallucinate
        stop=["<|user|>"]
    )
    
    return output['choices'][0]['text'].strip()

# TEST
query = "What was LlamaCorp's revenue and where was it founded?"
print("\nQuery:", query)
answer = rag_query(query)
print("\nModel response:", answer)