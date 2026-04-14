#!/usr/bin/env python3
"""
Test script to verify llama.cpp embedding model (nomic-embed-text-v1.5) functionality.
"""
import os
import sys

def test_llama_cpp_embedding():
    """Test llama.cpp embedding model using llama-cpp-python."""
    try:
        from llama_cpp import Llama
        
        print("=" * 60)
        print("Testing llama-cpp-python embedding API")
        print("=" * 60)
        
        model_path = os.environ.get(
            "EMBED_MODEL_PATH",
            "./models/embeddings/nomic-embed-text-v1.5.Q4_K_M.gguf",
        )
        
        # Load embedding model with embedding=True (required for llama-cpp-python >= 0.2.80)
        llm = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_batch=512,
            n_threads=4,
            use_mmap=True,
            use_lock=True,
            embedding=True,  # Critical: enables embedding mode
        )
        
        # Test Ukrainian texts
        ukrainian_texts = [
            "Який дохід мала компанія LlamaCorp?",
            "Де заснована компанія LlamaCorp?",
            "Що є головним продуктом компанії?"
        ]
        
        print(f"\nGenerating embeddings for {len(ukrainian_texts)} Ukrainian texts...")
        
        # Method 1: Using create_embedding
        embeddings = llm.create_embedding(ukrainian_texts)
        
        print(f"\n✅ Successfully created embeddings!")
        print(f"Number of texts: {len(ukrainian_texts)}")
        print(f"Embedding dimensions: {len(embeddings['data'][0]['embedding'])}")
        print(f"Embedding dtype: float32")
        print(f"Sample embedding (first 10 values): {embeddings['data'][0]['embedding'][:10]}")
        
        # Verify all embeddings have same dimension
        dims = [len(e['embedding']) for e in embeddings['data']]
        if len(set(dims)) == 1:
            print(f"\n✅ All embeddings have consistent dimension: {dims[0]}")
        
        print("\n✅ llama-cpp-python embedding API is WORKING!")
        return True
            
    except ImportError as e:
        print(f"\n❌ llama-cpp-python not installed: {e}")
        print("   Install with: pip install llama-cpp-python")
        return False
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_llama_cpp_embedding()
    sys.exit(0 if success else 1)
