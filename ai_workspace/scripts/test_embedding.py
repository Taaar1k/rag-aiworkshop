#!/usr/bin/env python3
"""
Test script to verify embedding model functionality.
"""
from sentence_transformers import SentenceTransformer

def test_embedding():
    try:
        print("Testing embedding model...")
        embedder = SentenceTransformer('paraphrase-multilingual-MiniLM-L12-v2')
        
        # Test Ukrainian text
        ukrainian_texts = [
            "Який дохід мала компанія LlamaCorp?",
            "Де заснована компанія LlamaCorp?",
            "Що є головним продуктом компанії?"
        ]
        
        embeddings = embedder.encode(ukrainian_texts)
        print(f"✅ Successfully created embeddings for {len(ukrainian_texts)} Ukrainian texts")
        print(f"Embedding shape: {embeddings.shape}")
        print(f"Embedding dtype: {embeddings.dtype}")
        return True
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_embedding()
    exit(0 if success else 1)
