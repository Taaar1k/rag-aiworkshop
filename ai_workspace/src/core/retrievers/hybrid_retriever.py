"""
Hybrid Retriever for RAG System.

Implements ensemble retrieval combining vector (semantic) and BM25 (keyword) search
using Reciprocal Rank Fusion (RRF) for optimal result ranking.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from collections import defaultdict

from langchain_core.documents import Document


@dataclass
class HybridRetrieverConfig:
    """Configuration for hybrid retriever."""
    vector_weight: float = 0.3
    keyword_weight: float = 0.7
    rrf_k: float = 60  # RRF constant (lower = more emphasis on top ranks)
    top_k: int = 10
    deduplicate: bool = True
    min_vector_score: float = 0.0
    min_keyword_score: float = 0.0
    latency_threshold_ms: float = 10.0


class HybridRetriever:
    """
    Hybrid retriever combining vector and keyword search via RRF.
    
    Features:
    - Reciprocal Rank Fusion (RRF) algorithm
    - Configurable weights for vector/keyword balance
    - Automatic deduplication by document chunk ID
    - Latency monitoring and optimization
    
    Args:
        vector_retriever: Vector search retriever (e.g., Chroma-based)
        keyword_retriever: Keyword search retriever (BM25)
        config: Hybrid retriever configuration
    """
    
    def __init__(
        self,
        vector_retriever: Any,
        keyword_retriever: Any,
        config: Optional[HybridRetrieverConfig] = None
    ):
        self.vector_retriever = vector_retriever
        self.keyword_retriever = keyword_retriever
        self.config = config or HybridRetrieverConfig()
        
        # Performance tracking
        self._latency_samples: List[float] = []
        self._max_latency_samples = 100
    
    def _reciprocal_rank_fusion(
        self,
        vector_results: List[Tuple[int, Document, float]],
        keyword_results: List[Tuple[int, Document, float]],
        rrf_k: float = 60.0
    ) -> List[Tuple[int, Document, float, str]]:
        """
        Apply Reciprocal Rank Fusion algorithm to combine rankings.
        
        RRF formula: score = sum(1 / (rank + k) for each ranking)
        
        Args:
            vector_results: List of (original_idx, document, vector_score)
            keyword_results: List of (original_idx, document, keyword_score)
            rrf_k: RRF constant (default 60)
            
        Returns:
            List of (rrf_score, document, vector_score, keyword_score, source)
        """
        # Build rank maps for each source
        vector_ranks: Dict[str, int] = {}  # doc_id -> rank
        keyword_ranks: Dict[str, int] = {}
        
        for rank, (_, doc, _) in enumerate(vector_results, start=1):
            doc_id = self._get_doc_id(doc)
            vector_ranks[doc_id] = rank
        
        for rank, (_, doc, _) in enumerate(keyword_results, start=1):
            doc_id = self._get_doc_id(doc)
            keyword_ranks[doc_id] = rank
        
        # Calculate RRF scores
        rrf_scores: Dict[str, float] = defaultdict(float)
        vector_scores: Dict[str, float] = {}
        keyword_scores: Dict[str, float] = {}
        
        # Vector contribution
        for _, doc, vec_score in vector_results:
            doc_id = self._get_doc_id(doc)
            rrf_scores[doc_id] += 1.0 / (vector_ranks.get(doc_id, float('inf')) + rrf_k)
            vector_scores[doc_id] = vec_score
        
        # Keyword contribution
        for _, doc, kw_score in keyword_results:
            doc_id = self._get_doc_id(doc)
            rrf_scores[doc_id] += 1.0 / (keyword_ranks.get(doc_id, float('inf')) + rrf_k)
            keyword_scores[doc_id] = kw_score
        
        # Sort by RRF score
        fused_results = sorted(
            rrf_scores.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Build final results with scores
        final_results = []
        for doc_id, rrf_score in fused_results:
            doc = self._find_document_by_id(
                vector_results + keyword_results,
                doc_id
            )
            if doc:
                final_results.append((
                    rrf_score,
                    doc,
                    vector_scores.get(doc_id, 0.0),
                    keyword_scores.get(doc_id, 0.0),
                    "hybrid"
                ))
        
        return final_results
    
    def _get_doc_id(self, doc: Document) -> str:
        """Get unique document ID for deduplication."""
        # Priority order for ID extraction
        if hasattr(doc, 'metadata') and 'item_id' in doc.metadata:
            return doc.metadata['item_id']
        if hasattr(doc, 'metadata') and 'doc_id' in doc.metadata:
            return doc.metadata['doc_id']
        if hasattr(doc, 'metadata') and 'id' in doc.metadata:
            return doc.metadata['id']
        # Fallback: hash of content
        return hash(doc.page_content)
    
    def _find_document_by_id(
        self,
        results: List[Tuple[int, Document, float]],
        doc_id: str
    ) -> Optional[Document]:
        """Find document by ID in result list."""
        for _, doc, _ in results:
            if self._get_doc_id(doc) == doc_id:
                return doc
        return None
    
    def _deduplicate(
        self,
        results: List[Tuple[float, Document, float, float, str]]
    ) -> List[Tuple[float, Document, float, float, str]]:
        """
        Remove duplicate documents, keeping highest-scoring version.
        
        Args:
            results: List of (rrf_score, doc, vector_score, keyword_score, source)
            
        Returns:
            Deduplicated list
        """
        seen_ids: Dict[str, Tuple[float, Document, float, float, str]] = {}
        
        for rrf_score, doc, vec_score, kw_score, source in results:
            doc_id = self._get_doc_id(doc)
            
            if doc_id not in seen_ids:
                seen_ids[doc_id] = (rrf_score, doc, vec_score, kw_score, source)
            else:
                # Keep highest RRF score
                if rrf_score > seen_ids[doc_id][0]:
                    seen_ids[doc_id] = (rrf_score, doc, vec_score, kw_score, source)
        
        return list(seen_ids.values())
    
    def _apply_weights(
        self,
        results: List[Tuple[float, Document, float, float, str]]
    ) -> List[Document]:
        """
        Apply configurable weights to final scores.
        
        Args:
            results: List of (rrf_score, doc, vector_score, keyword_score, source)
            
        Returns:
            List of Documents with weighted scores in metadata
        """
        weighted_results = []
        
        for rrf_score, doc, vec_score, kw_score, source in results:
            # Apply weights
            final_score = (
                self.config.vector_weight * vec_score +
                self.config.keyword_weight * kw_score
            )
            
            # Update document metadata
            if not hasattr(doc, 'metadata'):
                doc.metadata = {}
            
            doc.metadata.update({
                'hybrid_score': float(final_score),
                'vector_score': float(vec_score),
                'keyword_score': float(kw_score),
                'vector_weight': self.config.vector_weight,
                'keyword_weight': self.config.keyword_weight,
                'retrieval_type': 'hybrid'
            })
            
            weighted_results.append(doc)
        
        return weighted_results
    
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
        Execute hybrid search combining vector and keyword retrieval.
        
        Args:
            query: Search query string
            top_k: Number of results to return (uses config default if None)
            vector_k: Number of results from vector retriever
            keyword_k: Number of results from keyword retriever
            min_vector_score: Minimum vector score threshold
            min_keyword_score: Minimum keyword score threshold
            
        Returns:
            List of relevant documents sorted by fused score
        """
        start_time = time.time()
        
        # Use config defaults if not specified
        top_k = top_k or self.config.top_k
        min_vector_score = min_vector_score or self.config.min_vector_score
        min_keyword_score = min_keyword_score or self.config.min_keyword_score
        
        # Execute parallel searches
        vector_results = []
        keyword_results = []
        
        # Vector search
        vector_docs = self.vector_retriever.invoke(query, k=vector_k)
        vector_results = [
            (idx, doc, float(doc.metadata.get('score', 0.0)))
            for idx, doc in enumerate(vector_docs)
        ]
        
        # Keyword search
        keyword_docs = self.keyword_retriever.invoke(
            query, k=keyword_k, min_score=min_keyword_score
        )
        keyword_results = [
            (idx, doc, float(doc.metadata.get('bm25_score', 0.0)))
            for idx, doc in enumerate(keyword_docs)
        ]
        
        # Apply RRF fusion
        fused_results = self._reciprocal_rank_fusion(
            vector_results,
            keyword_results,
            rrf_k=self.config.rrf_k
        )
        
        # Deduplicate if enabled
        if self.config.deduplicate:
            fused_results = self._deduplicate(fused_results)
        
        # Apply weights and get final documents
        final_docs = self._apply_weights(fused_results)
        
        # Return top-k
        result = final_docs[:top_k]
        
        # Track latency
        latency_ms = (time.time() - start_time) * 1000
        self._track_latency(latency_ms)
        
        return result
    
    def _track_latency(self, latency_ms: float) -> None:
        """Track retrieval latency for monitoring."""
        self._latency_samples.append(latency_ms)
        
        # Keep only last N samples
        if len(self._latency_samples) > self._max_latency_samples:
            self._latency_samples = self._latency_samples[-self._max_latency_samples:]
    
    def get_performance_stats(self) -> Dict[str, Any]:
        """Get retrieval performance statistics."""
        if not self._latency_samples:
            return {"latency_samples": 0}
        
        import statistics
        
        return {
            "latency_samples": len(self._latency_samples),
            "avg_latency_ms": statistics.mean(self._latency_samples),
            "max_latency_ms": max(self._latency_samples),
            "min_latency_ms": min(self._latency_samples),
            "p95_latency_ms": sorted(self._latency_samples)[int(len(self._latency_samples) * 0.95)] if len(self._latency_samples) > 1 else 0,
            "latency_threshold_ms": self.config.latency_threshold_ms,
            "exceeds_threshold": any(l > self.config.latency_threshold_ms for l in self._latency_samples)
        }
    
    def set_weights(self, vector_weight: float, keyword_weight: float) -> None:
        """
        Update retrieval weights dynamically.
        
        Args:
            vector_weight: Weight for vector search (0.0-1.0)
            keyword_weight: Weight for keyword search (0.0-1.0)
        """
        total = vector_weight + keyword_weight
        self.config.vector_weight = vector_weight / total
        self.config.keyword_weight = keyword_weight / total
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return {
            "vector_weight": self.config.vector_weight,
            "keyword_weight": self.config.keyword_weight,
            "rrf_k": self.config.rrf_k,
            "top_k": self.config.top_k,
            "deduplicate": self.config.deduplicate,
            "min_vector_score": self.config.min_vector_score,
            "min_keyword_score": self.config.min_keyword_score,
            "latency_threshold_ms": self.config.latency_threshold_ms
        }
