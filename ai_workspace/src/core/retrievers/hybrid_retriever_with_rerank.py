"""
Hybrid Retriever with Cross-Encoder Reranking.

Extends the hybrid retriever with cross-encoder reranking for improved
relevance scoring. The pipeline:
1. Hybrid search (vector + BM25 via RRF)
2. Cross-encoder reranking of top-K results
3. Final ranked results with confidence scores
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from langchain_core.documents import Document

from ..rerankers.cross_encoder_reranker import CrossEncoderReranker, RerankerConfig


@dataclass
class HybridRetrieverWithRerankConfig:
    """Configuration for hybrid retriever with reranking."""
    # Hybrid search config
    vector_weight: float = 0.3
    keyword_weight: float = 0.7
    rrf_k: float = 60.0
    top_k: int = 10
    deduplicate: bool = True
    min_vector_score: float = 0.0
    min_keyword_score: float = 0.0
    latency_threshold_ms: float = 10.0
    
    # Reranker config
    rerank_enabled: bool = True
    rerank_top_k: int = 50  # Initial retrieval for reranking
    rerank_model: str = "BAAI/bge-reranker-large"
    rerank_device: str = "cpu"
    rerank_min_score: float = 0.0
    rerank_latency_threshold_ms: float = 20.0


class HybridRetrieverWithRerank:
    """
    Hybrid retriever with cross-encoder reranking.
    
    Combines the speed of hybrid search (vector + BM25) with the accuracy
    of cross-encoder reranking. This two-stage approach provides optimal
    balance between performance and relevance.
    
    Pipeline:
    1. Initial hybrid search retrieves top-K candidates (K=50)
    2. Cross-encoder reranks candidates for final relevance scoring
    3. Returns top-N results with confidence scores
    
    Features:
    - Configurable reranking (enable/disable)
    - Automatic model loading
    - Latency monitoring for both stages
    - A/B testing support
    
    Args:
        hybrid_retriever: Base hybrid retriever
        reranker: Cross-encoder reranker instance
        config: Configuration
    """
    
    def __init__(
        self,
        hybrid_retriever: Any,
        reranker: CrossEncoderReranker,
        config: Optional[HybridRetrieverWithRerankConfig] = None
    ):
        self.hybrid_retriever = hybrid_retriever
        self.reranker = reranker
        self.config = config or HybridRetrieverWithRerankConfig()
        
        # Performance tracking
        self._hybrid_latency_samples: List[float] = []
        self._rerank_latency_samples: List[float] = []
        self._max_samples = 100
        self._total_requests = 0
        self._rerank_enabled = self.config.rerank_enabled
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        vector_k: int = 10,
        keyword_k: int = 10,
        min_vector_score: Optional[float] = None,
        min_keyword_score: Optional[float] = None
    ) -> List[Document]:
        """
        Execute hybrid search with cross-encoder reranking.
        
        Args:
            query: Search query string
            top_k: Number of final results to return
            vector_k: Number of results from vector retriever
            keyword_k: Number of results from keyword retriever
            min_vector_score: Minimum vector score threshold
            min_keyword_score: Minimum keyword score threshold
            
        Returns:
            List of relevant documents sorted by relevance score
        """
        start_time = time.time()
        self._total_requests += 1
        
        # Use config defaults
        top_k = top_k or self.config.top_k
        min_vector_score = min_vector_score or self.config.min_vector_score
        min_keyword_score = min_keyword_score or self.config.min_keyword_score
        
        # Stage 1: Hybrid search
        hybrid_start = time.time()
        
        # Get initial candidates for reranking
        initial_top_k = self.config.rerank_top_k if self._rerank_enabled else top_k
        
        # Invoke hybrid retriever
        if hasattr(self.hybrid_retriever, 'retrieve'):
            initial_docs = self.hybrid_retriever.retrieve(
                query=query,
                top_k=initial_top_k,
                vector_k=vector_k,
                keyword_k=keyword_k,
                min_vector_score=min_vector_score,
                min_keyword_score=min_keyword_score
            )
        else:
            # Fallback for direct invoke
            initial_docs = self.hybrid_retriever.invoke(query, k=initial_top_k)
        
        hybrid_latency = (time.time() - hybrid_start) * 1000
        self._track_hybrid_latency(hybrid_latency)
        
        # Stage 2: Cross-encoder reranking (if enabled)
        if self._rerank_enabled and initial_docs:
            rerank_start = time.time()
            
            reranked_docs = self.reranker.rerank_with_metadata(
                query=query,
                documents=initial_docs,
                top_n=top_k,
                min_score=self.config.rerank_min_score
            )
            
            rerank_latency = (time.time() - rerank_start) * 1000
            self._track_rerank_latency(rerank_latency)
        else:
            # Skip reranking, apply hybrid scores
            reranked_docs = self._apply_hybrid_scores(initial_docs, top_k)
        
        # Final result
        result = reranked_docs[:top_k]
        
        # Track total latency
        total_latency = (time.time() - start_time) * 1000
        
        return result
    
    def _apply_hybrid_scores(
        self,
        docs: List[Document],
        top_k: int
    ) -> List[Document]:
        """Apply hybrid scores and return top-k documents."""
        scored_docs = []
        
        for doc in docs:
            if not hasattr(doc, 'metadata'):
                doc.metadata = {}
            
            hybrid_score = doc.metadata.get('hybrid_score', 0.0)
            vector_score = doc.metadata.get('vector_score', 0.0)
            keyword_score = doc.metadata.get('keyword_score', 0.0)
            
            doc.metadata.update({
                'hybrid_score': float(hybrid_score),
                'vector_score': float(vector_score),
                'keyword_score': float(keyword_score),
                'retrieval_type': 'hybrid',
                'rerank_enabled': False
            })
            
            scored_docs.append((doc, hybrid_score))
        
        # Sort by hybrid score
        scored_docs = sorted(scored_docs, key=lambda x: x[1], reverse=True)
        
        return [doc for doc, _ in scored_docs[:top_k]]
    
    def _track_hybrid_latency(self, latency_ms: float) -> None:
        """Track hybrid search latency."""
        self._hybrid_latency_samples.append(latency_ms)
        
        if len(self._hybrid_latency_samples) > self._max_samples:
            self._hybrid_latency_samples = self._hybrid_latency_samples[-self._max_samples:]
    
    def _track_rerank_latency(self, latency_ms: float) -> None:
        """Track reranking latency."""
        self._rerank_latency_samples.append(latency_ms)
        
        if len(self._rerank_latency_samples) > self._max_samples:
            self._rerank_latency_samples = self._rerank_latency_samples[-self._max_samples:]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get comprehensive performance statistics."""
        import statistics
        
        stats = {
            "total_requests": self._total_requests,
            "hybrid_search": {
                "latency_samples": len(self._hybrid_latency_samples),
                "avg_latency_ms": statistics.mean(self._hybrid_latency_samples) if self._hybrid_latency_samples else 0,
                "max_latency_ms": max(self._hybrid_latency_samples) if self._hybrid_latency_samples else 0,
                "min_latency_ms": min(self._hybrid_latency_samples) if self._hybrid_latency_samples else 0
            },
            "reranking": {
                "enabled": self._rerank_enabled,
                "latency_samples": len(self._rerank_latency_samples),
                "avg_latency_ms": statistics.mean(self._rerank_latency_samples) if self._rerank_latency_samples else 0,
                "max_latency_ms": max(self._rerank_latency_samples) if self._rerank_latency_samples else 0,
                "min_latency_ms": min(self._rerank_latency_samples) if self._rerank_latency_samples else 0
            },
            "reranker": self.reranker.get_performance_stats(),
            "config": {
                "rerank_enabled": self._rerank_enabled,
                "rerank_top_k": self.config.rerank_top_k,
                "top_k": self.config.top_k
            }
        }
        
        return stats
    
    def toggle_reranking(self, enabled: bool) -> None:
        """
        Enable or disable reranking dynamically.
        
        Args:
            enabled: True to enable reranking, False to disable
        """
        self._rerank_enabled = enabled
        print(f"Reranking {'enabled' if enabled else 'disabled'}")
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return {
            "vector_weight": self.config.vector_weight,
            "keyword_weight": self.config.keyword_weight,
            "rrf_k": self.config.rrf_k,
            "top_k": self.config.top_k,
            "rerank_enabled": self._rerank_enabled,
            "rerank_top_k": self.config.rerank_top_k,
            "rerank_model": self.config.rerank_model,
            "rerank_device": self.config.rerank_device
        }
