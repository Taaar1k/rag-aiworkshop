"""
Cross-Encoder Reranker for RAG System.

Implements reranking of search results using cross-encoder models for improved
relevance scoring. Cross-encoders evaluate query-document pairs jointly,
providing more accurate relevance scores than bi-encoders.
"""

import time
from dataclasses import dataclass, field
from typing import Any, List, Optional, Tuple
from pathlib import Path

from langchain_core.documents import Document

try:
    from sentence_transformers import CrossEncoder
except ImportError:
    raise ImportError(
        "sentence-transformers is required for CrossEncoderReranker. "
        "Install it with: pip install sentence-transformers"
    )


@dataclass
class RerankerConfig:
    """Configuration for cross-encoder reranker."""
    model_name: str = "BAAI/bge-reranker-large"
    device: str = "cpu"  # "cuda" for GPU acceleration
    top_k: int = 10
    max_chunks: int = 100  # Maximum chunks to rerank
    min_score: float = 0.0
    cache_dir: Optional[str] = None
    latency_threshold_ms: float = 20.0


class CrossEncoderReranker:
    """
    Cross-encoder reranker for improving search result relevance.
    
    Cross-encoders evaluate query-document pairs jointly, providing more accurate
    relevance scores than bi-encoders. They are slower but significantly more
    accurate (15-25% improvement in retrieval quality).
    
    Features:
    - Configurable model selection (BGE-Reranker, etc.)
    - Device support (CPU/GPU)
    - Latency monitoring
    - Score threshold filtering
    
    Args:
        config: Reranker configuration
    """
    
    def __init__(self, config: Optional[RerankerConfig] = None):
        self.config = config or RerankerConfig()
        self.model_name = self.config.model_name
        
        # Initialize cross-encoder model
        self._model = CrossEncoder(
            model_name=self.model_name,
            device=self.config.device,
            cache_folder=self.config.cache_dir
        )
        
        # Performance tracking
        self._latency_samples: List[float] = []
        self._max_latency_samples = 100
        self._rerank_count = 0
    
    def rerank(
        self,
        query: str,
        documents: List[Document],
        top_n: Optional[int] = None,
        min_score: Optional[float] = None
    ) -> List[Tuple[Document, float]]:
        """
        Rerank documents based on relevance to query using cross-encoder.
        
        Args:
            query: Search query string
            documents: List of document chunks to rerank
            top_n: Number of top results to return (uses config default if None)
            min_score: Minimum relevance score threshold
            
        Returns:
            List of (document, score) tuples sorted by relevance score
        """
        start_time = time.time()
        
        # Use config defaults
        top_n = top_n or self.config.top_k
        min_score = min_score or self.config.min_score
        
        # Limit to max_chunks for performance
        documents = documents[:self.config.max_chunks]
        
        if not documents:
            return []
        
        # Create query-document pairs for cross-encoder
        pairs = [[query, doc.page_content] for doc in documents]
        
        # Get relevance scores from cross-encoder
        scores = self._model.predict(pairs)
        
        # Pair documents with scores
        scored_docs = list(zip(documents, scores))
        
        # Filter by minimum score
        scored_docs = [(doc, score) for doc, score in scored_docs if score >= min_score]
        
        # Sort by score (descending)
        scored_docs = sorted(scored_docs, key=lambda x: x[1], reverse=True)
        
        # Return top_n results
        result = scored_docs[:top_n]
        
        # Track latency
        latency_ms = (time.time() - start_time) * 1000
        self._track_latency(latency_ms)
        self._rerank_count += 1
        
        return result
    
    def rerank_with_metadata(
        self,
        query: str,
        documents: List[Document],
        top_n: Optional[int] = None,
        min_score: Optional[float] = None
    ) -> List[Document]:
        """
        Rerank documents and attach scores to document metadata.
        
        Args:
            query: Search query string
            documents: List of document chunks to rerank
            top_n: Number of top results to return
            min_score: Minimum relevance score threshold
            
        Returns:
            List of Documents with rerank_score in metadata
        """
        scored_results = self.rerank(query, documents, top_n, min_score)
        
        reranked_docs = []
        for doc, score in scored_results:
            # Attach rerank score to metadata
            if not hasattr(doc, 'metadata'):
                doc.metadata = {}
            
            doc.metadata.update({
                'rerank_score': float(score),
                'rerank_model': self.model_name,
                'rerank_timestamp': time.time()
            })
            
            reranked_docs.append(doc)
        
        return reranked_docs
    
    def _track_latency(self, latency_ms: float) -> None:
        """Track reranking latency for monitoring."""
        self._latency_samples.append(latency_ms)
        
        # Keep only last N samples
        if len(self._latency_samples) > self._max_latency_samples:
            self._latency_samples = self._latency_samples[-self._max_latency_samples:]
    
    def get_performance_stats(self) -> dict:
        """Get reranker performance statistics."""
        if not self._latency_samples:
            return {
                "rerank_count": self._rerank_count,
                "latency_samples": 0
            }
        
        import statistics
        
        return {
            "rerank_count": self._rerank_count,
            "latency_samples": len(self._latency_samples),
            "avg_latency_ms": statistics.mean(self._latency_samples),
            "max_latency_ms": max(self._latency_samples),
            "min_latency_ms": min(self._latency_samples),
            "p95_latency_ms": sorted(self._latency_samples)[int(len(self._latency_samples) * 0.95)] if len(self._latency_samples) > 1 else 0,
            "latency_threshold_ms": self.config.latency_threshold_ms,
            "exceeds_threshold": any(l > self.config.latency_threshold_ms for l in self._latency_samples)
        }
    
    def get_config(self) -> dict:
        """Get current configuration."""
        return {
            "model_name": self.model_name,
            "device": self.config.device,
            "top_k": self.config.top_k,
            "max_chunks": self.config.max_chunks,
            "min_score": self.config.min_score,
            "latency_threshold_ms": self.config.latency_threshold_ms
        }
    
    def __del__(self):
        """Cleanup on deletion."""
        if hasattr(self, '_model'):
            del self._model
