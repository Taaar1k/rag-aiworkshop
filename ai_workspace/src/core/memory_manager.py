"""
Memory Manager for RAG System
Implements vector memory with ChromaDB.
"""

import os
import logging
import uuid

logger = logging.getLogger(__name__)

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

import chromadb
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class MemoryConfig:
    """Configuration for memory manager."""
    persist_directory: str = "./ai_workspace/memory/chroma_db"
    collection_prefix: str = "rag_"
    batch_size: int = 100
    max_collection_size: int = 10_000_000
    embedding_model: str = "nomic-ai/nomic-embed-text-v1.5"


class VectorMemory:
    """Vector Memory using ChromaDB."""

    def __init__(self, collection_name: str, config: MemoryConfig):
        self.collection_name = collection_name
        self.config = config
        self._client = None
        self._collection = None
        self._embeddings = None
        self._init()

    def _init(self):
        """Initialize ChromaDB client."""
        os.makedirs(self.config.persist_directory, exist_ok=True)
        
        self._client = chromadb.PersistentClient(
            path=self.config.persist_directory
        )
        
        self._collection = self._client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            self._embeddings = HuggingFaceEmbeddings(
                model_name=self.config.embedding_model,
                model_kwargs={"trust_remote_code": True}
            )
        except Exception as e:
            logger.warning("Failed to load embeddings: %s", e)

    def add(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add document to memory."""
        if self._embeddings is None:
            raise RuntimeError("Embeddings not available")
        
        item_id = str(uuid.uuid4())
        meta = metadata or {}
        meta.update({
            "timestamp": datetime.now().isoformat(),
            "item_id": item_id
        })
        
        embedding = self._embeddings.embed_documents([content])[0]
        
        self._collection.add(
            documents=[content],
            embeddings=[embedding],
            metadatas=[meta],
            ids=[item_id]
        )
        
        return item_id

    def search(self, query: str, k: int = 5, filter_metadata: Optional[Dict[str, Any]] = None) -> List[Document]:
        """Search vector memory."""
        if self._embeddings is None:
            return []
        
        where_filter = filter_metadata or {}
        
        try:
            results = self._collection.query(
                query_embeddings=self._embeddings.embed_documents([query]),
                n_results=k,
                where=where_filter
            )
        except Exception as e:
            logger.warning("Search failed: %s", e)
            return []
        
        documents = []
        if results.get("documents") and results["documents"][0]:
            for i, doc_content in enumerate(results["documents"][0]):
                documents.append(Document(
                    page_content=doc_content,
                    metadata=results["metadatas"][0][i] if results.get("metadatas") else {}
                ))
        
        return documents

    def delete(self, memory_id: str) -> bool:
        """Delete document by ID."""
        try:
            self._collection.delete(ids=[memory_id])
            return True
        except Exception:
            return False

    def count(self) -> int:
        """Get document count."""
        return self._collection.count()

    def clear(self) -> None:
        """Clear all data."""
        self._client.delete_collection(self.collection_name)
        self._init()


class MemoryManager:
    """Factory for creating vector memories."""

    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self._memories: Dict[str, VectorMemory] = {}

    def get_memory(self, collection_name: str = "default") -> VectorMemory:
        """Get or create vector memory."""
        if collection_name not in self._memories:
            full_name = f"{self.config.collection_prefix}{collection_name}"
            self._memories[collection_name] = VectorMemory(full_name, self.config)
        return self._memories[collection_name]

    def get_vector_memory(self, model_id: str = "default") -> VectorMemory:
        """Get or create vector memory (alias for get_memory)."""
        return self.get_memory(model_id)

    def cleanup(self) -> Dict[str, int]:
        """Cleanup overloaded collections."""
        return {}

    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all memories."""
        return {k: {"vector_count": v.count()} for k, v in self._memories.items()}

    def delete_documents_by_source(self, source: str) -> int:
        """Delete documents by source."""
        mem = self.get_memory("default")
        try:
            mem._collection.delete(where={"source": source})
            return 1
        except Exception:
            return 0

    def get_stats_by_source(self) -> Dict[str, Any]:
        """Get statistics grouped by source."""
        return {"sources": {}, "total_documents": 0}

    def close(self) -> None:
        """Close all connections."""
        self._memories.clear()


_memory_manager: Optional[MemoryManager] = None


def get_memory_manager(config: Optional[MemoryConfig] = None) -> MemoryManager:
    """Get or create global memory manager."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(config)
    return _memory_manager


def reset_memory_manager() -> None:
    """Reset global memory manager."""
    global _memory_manager
    if _memory_manager:
        _memory_manager.close()
    _memory_manager = None
