"""
Hybrid Graph Retriever for Graph RAG System.

Combines graph-based retrieval with vector search for enhanced information retrieval.
Implements hybrid scoring and result fusion for optimal query results.
"""

import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

from langchain_core.documents import Document

from .graph_retriever import GraphRetriever, GraphRetrieverConfig
from .entity_extractor import EntityExtractor


@dataclass
class HybridGraphRetrieverConfig:
    """Configuration for hybrid graph retriever."""
    vector_weight: float = 0.5
    graph_weight: float = 0.5
    top_k: int = 10
    graph_depth: int = 2
    min_graph_score: float = 0.3
    min_vector_score: float = 0.3
    use_reranking: bool = True
    rerank_weight: float = 0.3


class HybridGraphRetriever:
    """
    Hybrid retriever combining graph and vector search.
    
    Features:
    - Simultaneous graph and vector retrieval
    - Result fusion using weighted scoring
    - Optional reranking for improved relevance
    - Performance monitoring
    
    Args:
        graph_retriever: GraphRetriever instance
        vector_retriever: Vector retriever (e.g., Chroma-based)
        config: Hybrid retriever configuration
    """
    
    def __init__(
        self,
        graph_retriever: GraphRetriever,
        vector_retriever: Any,
        config: Optional[HybridGraphRetrieverConfig] = None
    ):
        self.graph_retriever = graph_retriever
        self.vector_retriever = vector_retriever
        self.config = config or HybridGraphRetrieverConfig()
        
        # Performance tracking
        self._latency_samples: List[float] = []
        self._max_latency_samples = 100
        
        # Entity extractor
        self.entity_extractor = EntityExtractor()
    
    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        graph_depth: Optional[int] = None
    ) -> List[Document]:
        """
        Retrieve results using both graph and vector search.
        
        Args:
            query: Search query string
            top_k: Number of results to return (uses config default if None)
            graph_depth: Graph traversal depth (uses config default if None)
            
        Returns:
            List of documents from combined retrieval
        """
        start_time = time.time()
        
        top_k = top_k or self.config.top_k
        graph_depth = graph_depth or self.config.graph_depth
        
        # Extract entities from query
        entities = self.entity_extractor.extract_entities(query)
        
        # Execute both retrievals in parallel
        vector_results = self._retrieve_vector(query)
        graph_results = self._retrieve_graph(query, graph_depth)
        
        # Combine results
        combined_results = self._combine_results(
            vector_results,
            graph_results,
            entities
        )
        
        # Rerank if enabled
        if self.config.use_reranking:
            combined_results = self._rerank_results(combined_results, query)
        
        # Limit to top_k
        result = combined_results[:top_k]
        
        # Track latency
        latency_ms = (time.time() - start_time) * 1000
        self._track_latency(latency_ms)
        
        return result
    
    def _retrieve_vector(self, query: str, k: int = 10) -> List[Tuple[Document, float]]:
        """
        Retrieve results using vector search.
        
        Args:
            query: Search query
            k: Number of results
            
        Returns:
            List of (document, score) tuples
        """
        try:
            docs = self.vector_retriever.invoke(query, k=k)
            results = []
            for doc in docs:
                score = float(doc.metadata.get('score', 0.5))
                results.append((doc, score))
            return results
        except Exception as e:
            print(f"Vector retrieval failed: {e}")
            return []
    
    def _retrieve_graph(self, query: str, depth: int = 2) -> List[Tuple[Document, float]]:
        """
        Retrieve results using graph traversal.
        
        Args:
            query: Search query
            depth: Graph traversal depth
            
        Returns:
            List of (document, score) tuples
        """
        try:
            graph_results = self.graph_retriever.retrieve_with_graph(query, depth=depth)
            
            # Convert graph results to documents
            results = []
            for item in graph_results:
                if item["type"] == "node":
                    node = item["data"]
                    doc = Document(
                        page_content=node.get("properties", {}).get("description", node.get("name", "")),
                        metadata={
                            "id": node.get("id"),
                            "labels": node.get("labels", []),
                            "graph_score": 0.8,
                            "source_entity": item.get("source_entity", "")
                        }
                    )
                    results.append((doc, 0.8))
                elif item["type"] == "relationship":
                    rel = item["data"]
                    doc = Document(
                        page_content=f"{rel['data'].get('start_node', '')} - {rel['type']} -> {rel['data'].get('end_node', '')}",
                        metadata={
                            "id": rel.get("id"),
                            "relationship_type": rel.get("type"),
                            "graph_score": 0.7,
                            "source_entity": item.get("source_entity", "")
                        }
                    )
                    results.append((doc, 0.7))
            
            return results
        except Exception as e:
            print(f"Graph retrieval failed: {e}")
            return []
    
    def _combine_results(
        self,
        vector_results: List[Tuple[Document, float]],
        graph_results: List[Tuple[Document, float]],
        entities: List[Any]
    ) -> List[Document]:
        """
        Combine vector and graph results using weighted scoring.
        
        Args:
            vector_results: Vector search results
            graph_results: Graph search results
            entities: Extracted entities from query
            
        Returns:
            Combined and scored documents
        """
        # Score maps for fusion
        vector_scores: Dict[str, float] = {}
        graph_scores: Dict[str, float] = {}
        
        # Process vector results
        for doc, score in vector_results:
            doc_id = self._get_doc_id(doc)
            vector_scores[doc_id] = score
        
        # Process graph results
        for doc, score in graph_results:
            doc_id = self._get_doc_id(doc)
            graph_scores[doc_id] = score
        
        # Get all unique document IDs
        all_doc_ids = set(vector_scores.keys()) | set(graph_scores.keys())
        
        # Combine scores using weighted average
        combined = []
        for doc_id in all_doc_ids:
            vec_score = vector_scores.get(doc_id, 0.0)
            graph_score = graph_scores.get(doc_id, 0.0)
            
            # Weighted combination
            final_score = (
                self.config.vector_weight * vec_score +
                self.config.graph_weight * graph_score
            )
            
            # Get document (prefer vector if available)
            doc = None
            for d, s in vector_results:
                if self._get_doc_id(d) == doc_id:
                    doc = d
                    break
            if doc is None:
                for d, s in graph_results:
                    if self._get_doc_id(d) == doc_id:
                        doc = d
                        break
            
            if doc:
                # Update metadata with scores
                doc.metadata.update({
                    "hybrid_score": final_score,
                    "vector_score": vec_score,
                    "graph_score": graph_score,
                    "retrieval_type": "hybrid_graph"
                })
                combined.append(doc)
        
        # Sort by combined score
        combined.sort(key=lambda d: d.metadata.get("hybrid_score", 0.0), reverse=True)
        
        return combined
    
    def _rerank_results(
        self,
        results: List[Document],
        query: str
    ) -> List[Document]:
        """
        Rerank results based on query relevance.
        
        Args:
            results: Results to rerank
            query: Original query
            
        Returns:
            Reranked results
        """
        # Simple reranking: boost results with entity matches
        query_entities = {e.name.lower() for e in self.entity_extractor.extract_entities(query)}
        
        reranked = []
        for doc in results:
            doc_text = doc.page_content.lower()
            doc_metadata = doc.metadata
            
            # Count entity matches
            entity_matches = sum(1 for e in query_entities if e in doc_text)
            
            # Boost score based on entity matches
            entity_boost = min(entity_matches * self.config.rerank_weight, 0.3)
            
            # Update score
            new_score = doc_metadata.get("hybrid_score", 0.0) + entity_boost
            doc_metadata["hybrid_score"] = min(new_score, 1.0)
            doc_metadata["entity_matches"] = entity_matches
            
            reranked.append(doc)
        
        # Re-sort by updated score
        reranked.sort(key=lambda d: d.metadata.get("hybrid_score", 0.0), reverse=True)
        
        return reranked
    
    def _get_doc_id(self, doc: Document) -> str:
        """Get unique document ID."""
        if hasattr(doc, 'metadata') and 'id' in doc.metadata:
            return str(doc.metadata['id'])
        if hasattr(doc, 'metadata') and 'doc_id' in doc.metadata:
            return str(doc.metadata['doc_id'])
        return str(hash(doc.page_content))
    
    def _track_latency(self, latency_ms: float) -> None:
        """Track retrieval latency for monitoring."""
        self._latency_samples.append(latency_ms)
        
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
            "p95_latency_ms": sorted(self._latency_samples)[int(len(self._latency_samples) * 0.95)] if len(self._latency_samples) > 1 else 0
        }
    
    def set_weights(self, vector_weight: float, graph_weight: float) -> None:
        """
        Update retrieval weights dynamically.
        
        Args:
            vector_weight: Weight for vector search (0.0-1.0)
            graph_weight: Weight for graph search (0.0-1.0)
        """
        total = vector_weight + graph_weight
        self.config.vector_weight = vector_weight / total
        self.config.graph_weight = graph_weight / total
    
    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return {
            "vector_weight": self.config.vector_weight,
            "graph_weight": self.config.graph_weight,
            "top_k": self.config.top_k,
            "graph_depth": self.config.graph_depth,
            "min_graph_score": self.config.min_graph_score,
            "min_vector_score": self.config.min_vector_score,
            "use_reranking": self.config.use_reranking
        }
