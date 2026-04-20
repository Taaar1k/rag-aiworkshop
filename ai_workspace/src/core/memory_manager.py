"""
Memory Manager for RAG System
Implements type-separated memory architecture with ChromaDB integration.

Memory Types:
- Vector Memory: ChromaDB collections for embedding vectors
"""

import os
import json
import logging
import uuid

logger = logging.getLogger(__name__)
from abc import ABC, abstractmethod
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Union
from dataclasses import dataclass, field

import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


@dataclass
class MemoryConfig:
    """Configuration for memory manager."""
    persist_directory: str = "./ai_workspace/memory/chroma_db"
    collection_prefix: str = "rag_"
    metadata_index_fields: List[str] = field(default_factory=lambda: ["model_id", "type", "timestamp"])
    batch_size: int = 100
    max_collection_size: int = 10_000_000
    session_ttl_hours: int = 24
    embedding_model: str = os.getenv("EMBEDDING_MODEL_NAME", "nomic-ai/nomic-embed-text-v1.5")


class MemoryBase(ABC):
    """Abstract base class for memory types."""
    
    @abstractmethod
    def add(self, data: Union[Document, Dict[str, Any], List[Document]]) -> str:
        """Add data to memory and return ID."""
        pass
    
    @abstractmethod
    def get(self, memory_id: str) -> Optional[Union[Document, Dict[str, Any]]]:
        """Get data by ID."""
        pass
    
    @abstractmethod
    def search(self, query: str, k: int = 5, **kwargs) -> List[Union[Document, Dict[str, Any]]]:
        """Search memory with query."""
        pass
    
    @abstractmethod
    def delete(self, memory_id: str) -> bool:
        """Delete data by ID."""
        pass
    
    @abstractmethod
    def clear(self) -> None:
        """Clear all data."""
        pass


class VectorMemory(MemoryBase):
    """
    Vector Memory using ChromaDB for embedding vectors.
    
    Features:
    - Persistent storage with metadata indexing
    - Automatic collection creation per model
    - Batch operations for performance
    - Metadata filtering
    """
    
    def __init__(self, config: MemoryConfig, model_id: str, collection_name: Optional[str] = None):
        self.model_id = model_id
        self.collection_name = collection_name or f"{config.collection_prefix}{model_id}"
        self.config = config
        
        # Initialize ChromaDB client
        self._init_chromadb()
        
        # Initialize LangChain vector store
        self._init_langchain_store()
        
        # Text splitter for document processing
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=512,
            chunk_overlap=50,
            separators=["\n\n", "\n", " ", ""]
        )

    def _init_chromadb(self):
        """Initialize ChromaDB client with persistent storage."""
        os.makedirs(self.config.persist_directory, exist_ok=True)
        
        self.chroma_client = chromadb.PersistentClient(
            path=self.config.persist_directory
        )
        
        # Create or get collection
        self.collection = self.chroma_client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"}
        )
        
        # Metadata indexing is handled automatically by ChromaDB
        # (create_index was deprecated/removed in newer versions)
    
    def _init_langchain_store(self):
        """Initialize LangChain vector store wrapper."""
        self.embeddings = HuggingFaceEmbeddings(
            model_name=self.config.embedding_model
        )
        
        self.vector_store = Chroma(
            client=self.chroma_client,
            collection_name=self.collection_name,
            embedding_function=self.embeddings,
            persist_directory=self.config.persist_directory
        )
    
    def add(
        self,
        data: Union[Document, Dict[str, Any], List[Document]],
        metadata: Optional[Dict[str, Any]] = None
    ) -> str:
        """
        Add data to vector memory.
        
        Args:
            data: Document, dict, or list of documents
            metadata: Additional metadata to store
            
        Returns:
            ID of added item
        """
        if isinstance(data, dict):
            doc = Document(page_content=str(data.get("content", "")), metadata=data)
        elif isinstance(data, Document):
            doc = data
        else:
            # List of documents
            ids = []
            for item in data:
                if isinstance(item, dict):
                    item = Document(page_content=str(item.get("content", "")), metadata=item)
                ids.append(self.add(item, metadata))
            return ids[0] if len(ids) == 1 else ids
        
        # Add metadata
        if metadata:
            doc.metadata.update(metadata)
        
        # Add model_id and timestamp
        doc.metadata.setdefault("model_id", self.model_id)
        doc.metadata.setdefault("type", "vector")
        doc.metadata["timestamp"] = datetime.now().isoformat()
        
        # Generate unique ID
        item_id = str(uuid.uuid4())
        doc.metadata["item_id"] = item_id
        
        # Add to ChromaDB
        self.collection.add(
            documents=[doc.page_content],
            embeddings=self.embeddings.embed_documents([doc.page_content]),
            metadatas=[doc.metadata],
            ids=[item_id]
        )
        
        return item_id
    
    def get(self, memory_id: str) -> Optional[Document]:
        """Get document by ID."""
        try:
            result = self.collection.get(
                ids=[memory_id],
                include=["documents", "metadatas"]
            )
            
            if not result["documents"] or not result["documents"][0]:
                return None
            
            return Document(
                page_content=result["documents"][0],
                metadata=result["metadatas"][0]
            )
        except Exception:
            return None
    
    def search(
        self,
        query: str,
        k: int = 5,
        filter_metadata: Optional[Dict[str, Any]] = None
    ) -> List[Document]:
        """
        Search vector memory.
        
        Args:
            query: Search query
            k: Number of results to return
            filter_metadata: Metadata filter dict
            
        Returns:
            List of similar documents
        """
        # Build filter
        where_filter = {"model_id": self.model_id}
        if filter_metadata:
            where_filter.update(filter_metadata)
        
        # Search
        results = self.collection.query(
            query_embeddings=self.embeddings.embed_documents([query]),
            n_results=min(k, self.config.max_collection_size),
            where=where_filter
        )
        
        # Convert to Document objects
        documents = []
        if results["documents"] and results["documents"][0]:
            for i, doc_content in enumerate(results["documents"][0]):
                documents.append(Document(
                    page_content=doc_content,
                    metadata=results["metadatas"][0][i] if results["metadatas"] else {}
                ))
        
        return documents
    
    def delete(self, memory_id: str) -> bool:
        """Delete document by ID."""
        try:
            self.collection.delete(ids=[memory_id])
            return True
        except Exception:
            return False
    
    def clear(self) -> None:
        """Clear all data from collection."""
        self.chroma_client.delete_collection(self.collection_name)
        self._init_chromadb()
    
    def get_stats(self) -> Dict[str, Any]:
        """Get collection statistics."""
        count = self.collection.count()
        return {
            "collection_name": self.collection_name,
            "model_id": self.model_id,
            "vector_count": count,
            "max_size": self.config.max_collection_size,
            "is_overloaded": count >= self.config.max_collection_size
        }


class MemoryManager:
    """
    Factory pattern for creating and managing memory instances.
    
    Features:
    - Factory pattern for memory type creation
    - Automatic cleanup of stale entries
    - Metadata indexing
    - Batch operations support
    """
    
    def __init__(self, config: Optional[MemoryConfig] = None):
        self.config = config or MemoryConfig()
        self._memories: Dict[str, MemoryBase] = {}
    
    def get_vector_memory(self, model_id: str) -> VectorMemory:
        """Get or create vector memory for model."""
        if model_id not in self._memories:
            self._memories[model_id] = VectorMemory(self.config, model_id)
        return self._memories[model_id]
    
    def get_memory(self, memory_type: str, model_id: Optional[str] = None) -> MemoryBase:
        """Get memory by type."""
        if memory_type == "vector":
            return self.get_vector_memory(model_id or "default")
        else:
            raise ValueError(f"Unknown memory type: {memory_type}")
    
    def cleanup(self) -> Dict[str, int]:
        """
        Cleanup overloaded collections.
        
        Returns:
            Cleanup statistics
        """
        stats = {}
        
        # Check overloaded collections
        for model_id, memory in self._memories.items():
            if isinstance(memory, VectorMemory):
                memory_stats = memory.get_stats()
                if memory_stats["is_overloaded"]:
                    # Auto-cleanup oldest entries
                    memory.clear()
                    stats[f"overloaded_{model_id}"] = memory_stats["vector_count"]
        
        return stats
    
    def get_all_stats(self) -> Dict[str, Any]:
        """Get statistics for all memories."""
        stats = {}
        for model_id, memory in self._memories.items():
            stats[model_id] = memory.get_stats()
        return stats

    def delete_documents_by_source(self, source: str) -> int:
        """
        Delete all chunks from ChromaDB that have metadata['source'] == source.

        Args:
            source: The source file path to match.

        Returns:
            Number of documents deleted (or None if count unavailable).
        """
        vector_memory = self.get_vector_memory("default")
        try:
            result = vector_memory.collection.delete(where={"source": source})
            logger.info("Deleted documents for source: %s", source)
            return result
        except Exception as e:
            logger.error("Failed to delete documents by source %s: %s", source, e)
            return 0

    def get_stats_by_source(self) -> Dict[str, Any]:
        """
        Get statistics grouped by source file.

        Returns:
            Dict mapping source paths to their document counts.
        """
        vector_memory = self.get_vector_memory("default")
        try:
            # Get all documents with their metadata
            result = vector_memory.collection.get(
                include=["metadatas"]
            )
            stats: Dict[str, int] = {}
            if result["metadatas"]:
                for metadata in result["metadatas"]:
                    source = metadata.get("source", "unknown")
                    stats[source] = stats.get(source, 0) + 1
            return {"sources": stats, "total_documents": sum(stats.values())}
        except Exception as e:
            logger.error("Failed to get stats by source: %s", e)
            return {"sources": {}, "total_documents": 0}

    def close(self) -> None:
        """Close all memory connections."""
        self._memories.clear()


# Global instance
_memory_manager: Optional[MemoryManager] = None


def get_memory_manager(config: Optional[MemoryConfig] = None) -> MemoryManager:
    """Get or create global memory manager instance."""
    global _memory_manager
    if _memory_manager is None:
        _memory_manager = MemoryManager(config)
    return _memory_manager


def reset_memory_manager() -> None:
    """Reset global memory manager instance."""
    global _memory_manager
    if _memory_manager:
        _memory_manager.close()
    _memory_manager = None
