#!/usr/bin/env python3
"""
Test script for ChromaDB Vector Memory persistence.

Demonstrates:
1. Creating a VectorMemory instance
2. Adding documents with metadata
3. Searching by query
4. Verifying persistence on disk
5. Reloading from disk and searching again
"""

import os
import sys
import json
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / "src"))

from core.memory_manager import MemoryManager, MemoryConfig
from langchain_core.documents import Document


def main():
    print("=" * 70)
    print("ChromaDB Vector Memory Persistence Test")
    print("=" * 70)
    
    # Configuration
    persist_dir = str(project_root / "memory" / "chroma_db" / "test_persistence")
    print(f"\n[1] Persistence directory: {persist_dir}")
    
    # Create memory config
    config = MemoryConfig(
        persist_directory=persist_dir,
        collection_prefix="test_",
        embedding_model="sentence-transformers/all-MiniLM-L6-v2"
    )
    
    # Create memory manager
    print("[2] Creating MemoryManager...")
    mm = MemoryManager(config)
    
    # Get vector memory
    vector_mem = mm.get_vector_memory("test_model")
    print(f"    Collection: {vector_mem.collection_name}")
    
    # --- Step 1: Add documents ---
    print("\n[3] Adding documents to VectorMemory...")
    
    test_documents = [
        Document(
            page_content="Штучний інтелект (ШІ) — це галузь комп'ютерних наук, яка займається створенням систем, здатних виконувати завдання, які зазвичай вимагають людської інтелектуальної діяльності.",
            metadata={"source": "test/ai_ukrainian.txt", "topic": "ai", "language": "uk"}
        ),
        Document(
            page_content="Machine learning is a subset of artificial intelligence that provides systems the ability to automatically learn and improve from experience.",
            metadata={"source": "test/ml_english.txt", "topic": "ml", "language": "en"}
        ),
        Document(
            page_content="Нейронні мережі — це обчислювальні системи, що надихаються біологічними нейронами та властивостями людського мозку.",
            metadata={"source": "test/neural_ukrainian.txt", "topic": "neural", "language": "uk"}
        ),
        Document(
            page_content="Vector databases store data as high-dimensional vectors and are used for similarity search in RAG systems.",
            metadata={"source": "test/vector_db.txt", "topic": "vectors", "language": "en"}
        ),
    ]
    
    added_ids = []
    for doc in test_documents:
        doc_id = vector_mem.add(doc)
        added_ids.append(doc_id)
        print(f"    Added: '{doc.page_content[:50]}...' -> ID: {doc_id[:8]}...")
    
    print(f"\n    Total documents added: {len(added_ids)}")
    
    # --- Step 2: Search ---
    print("\n[4] Searching for documents...")
    
    queries = [
        ("штучний інтелект", "Ukrainian query about AI"),
        ("machine learning", "English query about ML"),
        ("нейронні мережі", "Ukrainian query about neural networks"),
    ]
    
    for query, description in queries:
        print(f"\n    Query: '{query}' ({description})")
        results = vector_mem.search(query, k=2)
        for i, result in enumerate(results):
            print(f"      Result {i+1}:")
            print(f"        Content: {result.page_content[:80]}...")
            print(f"        Metadata: {result.metadata}")
            print(f"        Item ID: {result.metadata.get('item_id', 'N/A')}")
    
    # --- Step 3: Verify persistence on disk ---
    print("\n[5] Verifying persistence on disk...")
    
    if os.path.exists(persist_dir):
        files = list(Path(persist_dir).rglob("*"))
        print(f"    Directory exists: {persist_dir}")
        print(f"    Files in directory: {len(files)}")
        for f in files[:10]:  # Show first 10 files
            size = f.stat().st_size if f.is_file() else 0
            print(f"      {f.relative_to(project_root)} ({size} bytes)")
    else:
        print(f"    WARNING: Directory does not exist: {persist_dir}")
    
    # --- Step 4: Reload from disk ---
    print("\n[6] Reloading VectorMemory from disk...")
    
    # Create a new instance (simulating restart)
    mm2 = MemoryManager(config)
    vector_mem2 = mm2.get_vector_memory("test_model")
    
    print(f"    Collection: {vector_mem2.collection_name}")
    count = vector_mem2.collection.count()
    print(f"    Documents in collection after reload: {count}")
    
    # --- Step 5: Search after reload ---
    print("\n[7] Searching after reload...")
    
    results = vector_mem2.search("штучний інтелект", k=2)
    if results:
        print(f"    Found {len(results)} results for 'штучний інтелект':")
        for i, result in enumerate(results):
            print(f"      Result {i+1}: {result.page_content[:80]}...")
    else:
        print("    No results found!")
    
    # --- Step 6: Stats ---
    print("\n[8] Memory statistics...")
    stats = vector_mem2.get_stats()
    print(f"    {json.dumps(stats, indent=4)}")
    
    # --- Cleanup ---
    print("\n[9] Cleanup...")
    print(f"    To remove test data, delete: {persist_dir}")
    print(f"    Run: rm -rf {persist_dir}")
    
    # Close connections
    mm.close()
    mm2.close()
    
    print("\n" + "=" * 70)
    print("Test completed successfully!")
    print("=" * 70)


if __name__ == "__main__":
    main()
