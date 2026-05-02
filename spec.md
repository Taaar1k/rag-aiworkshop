### SPEC.md

Choosing RAG (Retrieval-Augmented Generation) is probably the **most effective way** for local models when you need to work with large amounts of data (books, knowledge bases, code documentation) without overflowing RAM/VRAM.

However, this technology is not a magic wand, and it has its own complexities. Let's detail the pitfalls and how to practically assemble this system based on `llama.cpp`.

---

### Part 1: "Pitfalls" of RAG

When you start implementing RAG, you will encounter these problems:

1. **Embedding language problem (Multilingual problem):**
   You mentioned the `all-MiniLM-L6-v2` model. It's great, fast, but **it works mainly with English**. If your document is in Ukrainian, and you search in Ukrainian, the model won't understand the meaning and will return "garbage".
   * **Solution:** Use multilingual models, for example, `paraphrase-multilingual-MiniLM-L12-v2`, `intfloat/multilingual-e5-small` or `BAAI/bge-m3`.

2. **Chunking strategy problem:**
   If you just cut the text by 500 characters, you can tear sentences or code pieces in half. As a result, the vector database will find the piece, but the model won't understand the context.
   * **Solution:** Make chunking "with overlap". For example, each chunk has 500 tokens, but the last 50 tokens of the previous chunk are the first 50 tokens of the next one. Or split strictly by paragraphs/newline characters `\n\n`.

3. **Synthesis vs. Fact search:**
   RAG works perfectly for questions like: *"What is the punishment under article 185?"*. It will find the article and the model will answer. But RAG **works terribly** for questions like: *"Make a short summary of the entire document"*, because only 2-3 random pieces of text are extracted, not the entire document.

4. **"Lost in the middle":**
   Research shows: if you give the LLM 5 found paragraphs, it pays good attention to the first and last, but often ignores information in the middle.
   * **Solution:** Limit the number of found chunks (to 3-4) and put the most relevant one at the very beginning or end of the prompt.

---

### Part 2: How to implement this with `llama.cpp`

`llama.cpp` itself is an engine for text generation. To make RAG, we need an "orchestrator" that will work with vectors. It's best to do this in **Python**, using the `llama-cpp-python` library.

Here's the concept of how this should work. We will need 2 libraries:
* `llama-cpp-python` (for generating responses with a large model).
* `sentence-transformers` or `chromadb` (for searching relevant chunks).

#### Step 1: Installing dependencies
```bash
pip install llama-cpp-python sentence-transformers scikit-learn numpy
```

#### Step 2: Writing code in Python (Simple RAG)

Here is a ready basic example of how to combine local embeddings and `llama.cpp` without heavy databases:

```python
import numpy as np
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from llama_cpp import Llama

# 1. Load multilingual model for creating embeddings (takes ~400 MB)
print("Loading embedding model...")
embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')

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
doc_embeddings = embedder.encode(documents)

def rag_query(user_query, top_k=2):
    # A) Vectorize user query
    query_embedding = embedder.encode([user_query])
    
    # B) Search similarity between query and documents (Cosine similarity)
    similarities = cosine_similarity(query_embedding, doc_embeddings)[0]
    
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
```

### How this optimizes resources with `llama.cpp`:
1. **RAM/VRAM savings:** Llama-3 models with 8192 token context need about 1-1.5 GB of additional memory ONLY for KV cache. If you have a book of 100,000 words, you wouldn't load it at all. Thanks to RAG, we set `n_ctx=2048` (or even 1024), which saves a huge amount of memory.
2. **Speed (Time to First Token):** `llama.cpp` takes a very long time to process the initial prompt (Prompt Processing) if it's large. Processing 8000 tokens can take 10-20 seconds on a weak PC. Processing 2 found paragraphs + question (about 300 tokens) — less than 1 second.
3. **Fewer hallucinations:** When the model has a huge context, it can start confusing facts from different ends of the document. RAG narrows the focus to 2-3 paragraphs.

### What to improve next for a serious tool?
If you want to make this not just a script, but a reliable tool, it's worth adding a database (for example, **ChromaDB**). It automatically saves vectors to disk. That is, you won't have to recalculate embeddings for documents every time you run the script. You will index your files once, and then the search will take milliseconds.

What do you think about this approach? Is it worth showing how to integrate real PDF reading or creating a database via ChromaDB here?