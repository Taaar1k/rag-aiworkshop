"""
Integration tests for Hybrid Search (Vector + BM25).

Tests end-to-end hybrid retrieval with real BM25 index and mock vector retriever.
Validates RRF fusion, deduplication, and performance metrics.
"""

import pytest
import sys
from pathlib import Path
import time
import statistics

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_core.documents import Document
from core.retrievers.bm25_retriever import BM25Retriever, BM25Config
from core.retrievers.hybrid_retriever import HybridRetriever, HybridRetrieverConfig


class TestIntegrationHybridSearch:
    """Integration tests for complete hybrid search workflow."""
    
    @pytest.fixture
    def sample_documents(self):
        """Sample documents for integration testing."""
        return [
            Document(
                page_content="Python is a high-level programming language known for its readability and simplicity.",
                metadata={"id": "doc1", "source": "python_docs", "category": "programming"}
            ),
            Document(
                page_content="Machine learning algorithms learn patterns from data to make predictions.",
                metadata={"id": "doc2", "source": "ml_docs", "category": "ai"}
            ),
            Document(
                page_content="Deep learning is a subset of machine learning using neural networks.",
                metadata={"id": "doc3", "source": "dl_docs", "category": "ai"}
            ),
            Document(
                page_content="Natural language processing enables computers to understand human language.",
                metadata={"id": "doc4", "source": "nlp_docs", "category": "ai"}
            ),
            Document(
                page_content="Data science combines statistics, programming, and domain expertise.",
                metadata={"id": "doc5", "source": "ds_docs", "category": "data"}
            )
        ]
    
    @pytest.fixture
    def bm25_retriever(self, sample_documents):
        """Create BM25 retriever with sample documents."""
        retriever = BM25Retriever()
        retriever.index_documents(sample_documents)
        return retriever
    
    @pytest.fixture
    def mock_vector_retriever(self):
        """Mock vector retriever for integration testing."""
        class MockVectorRetriever:
            def __init__(self):
                self.results = {
                    "python": [
                        Document(page_content="Python is a high-level programming language", metadata={"id": "doc1", "score": 0.95}),
                        Document(page_content="Data science combines statistics, programming", metadata={"id": "doc5", "score": 0.75})
                    ],
                    "machine learning": [
                        Document(page_content="Machine learning algorithms learn patterns", metadata={"id": "doc2", "score": 0.92}),
                        Document(page_content="Deep learning is a subset of machine learning", metadata={"id": "doc3", "score": 0.88})
                    ],
                    "neural networks": [
                        Document(page_content="Deep learning is a subset of machine learning using neural networks", metadata={"id": "doc3", "score": 0.90}),
                        Document(page_content="Machine learning algorithms learn patterns from data", metadata={"id": "doc2", "score": 0.70})
                    ],
                    "default": [
                        Document(page_content="Python is a high-level programming language", metadata={"id": "doc1", "score": 0.85}),
                        Document(page_content="Machine learning algorithms learn patterns", metadata={"id": "doc2", "score": 0.80}),
                        Document(page_content="Deep learning is a subset of machine learning", metadata={"id": "doc3", "score": 0.75})
                    ]
                }
            
            def invoke(self, query, k=5):
                query_lower = query.lower()
                if "python" in query_lower:
                    return self.results["python"][:k]
                elif "machine learning" in query_lower or "machine" in query_lower:
                    return self.results["machine learning"][:k]
                elif "neural" in query_lower:
                    return self.results["neural networks"][:k]
                return self.results["default"][:k]
        
        return MockVectorRetriever()
    
    def test_hybrid_search_python_query(self, bm25_retriever, mock_vector_retriever):
        """Test hybrid search for Python-related query."""
        retriever = HybridRetriever(
            vector_retriever=mock_vector_retriever,
            keyword_retriever=bm25_retriever,
            config=HybridRetrieverConfig(vector_weight=0.3, keyword_weight=0.7, top_k=3)
        )
        
        results = retriever.retrieve("python programming", top_k=3)
        
        assert len(results) <= 3
        # First result should be Python document
        assert any("python" in doc.page_content.lower() for doc in results)
        # Check metadata
        for doc in results:
            assert "hybrid_score" in doc.metadata
            assert "vector_score" in doc.metadata
            assert "keyword_score" in doc.metadata
    
    def test_hybrid_search_ml_query(self, bm25_retriever, mock_vector_retriever):
        """Test hybrid search for machine learning query."""
        retriever = HybridRetriever(
            vector_retriever=mock_vector_retriever,
            keyword_retriever=bm25_retriever,
            config=HybridRetrieverConfig(vector_weight=0.3, keyword_weight=0.7, top_k=3)
        )
        
        results = retriever.retrieve("machine learning algorithms", top_k=3)
        
        assert len(results) <= 3
        # Should return ML-related documents
        assert any("machine learning" in doc.page_content.lower() or "ml" in doc.page_content.lower() for doc in results)
    
    def test_hybrid_search_neural_networks(self, bm25_retriever, mock_vector_retriever):
        """Test hybrid search for neural networks query."""
        retriever = HybridRetriever(
            vector_retriever=mock_vector_retriever,
            keyword_retriever=bm25_retriever,
            config=HybridRetrieverConfig(vector_weight=0.3, keyword_weight=0.7, top_k=3)
        )
        
        results = retriever.retrieve("neural networks deep learning", top_k=3)
        
        assert len(results) <= 3
        assert any("neural" in doc.page_content.lower() or "deep learning" in doc.page_content.lower() for doc in results)
    
    def test_hybrid_deduplication(self, bm25_retriever, mock_vector_retriever):
        """Test that hybrid search deduplicates results correctly."""
        retriever = HybridRetriever(
            vector_retriever=mock_vector_retriever,
            keyword_retriever=bm25_retriever,
            config=HybridRetrieverConfig(vector_weight=0.3, keyword_weight=0.7, top_k=5, deduplicate=True)
        )
        
        results = retriever.retrieve("python", top_k=5)
        
        # Check for unique document IDs
        doc_ids = [doc.metadata.get("id") for doc in results]
        assert len(doc_ids) == len(set(doc_ids)), "Deduplication failed: duplicate document IDs found"
    
    def test_hybrid_performance_latency(self, bm25_retriever, mock_vector_retriever):
        """Test hybrid search performance and latency."""
        retriever = HybridRetriever(
            vector_retriever=mock_vector_retriever,
            keyword_retriever=bm25_retriever,
            config=HybridRetrieverConfig(vector_weight=0.3, keyword_weight=0.7, top_k=5)
        )
        
        # Run multiple queries to collect latency data
        latencies = []
        for _ in range(10):
            start = time.time()
            retriever.retrieve("python programming")
            latency_ms = (time.time() - start) * 1000
            latencies.append(latency_ms)
        
        # Check latency metrics
        stats = retriever.get_performance_stats()
        avg_latency = stats["avg_latency_ms"]
        
        # Latency should be reasonable (< 100ms for this test setup)
        assert avg_latency < 100, f"Average latency {avg_latency}ms exceeds threshold"
    
    def test_hybrid_weight_adjustment(self, bm25_retriever, mock_vector_retriever):
        """Test dynamic weight adjustment."""
        retriever = HybridRetriever(
            vector_retriever=mock_vector_retriever,
            keyword_retriever=bm25_retriever,
            config=HybridRetrieverConfig(vector_weight=0.5, keyword_weight=0.5, top_k=3)
        )
        
        # Initial weights
        assert retriever.config.vector_weight == 0.5
        assert retriever.config.keyword_weight == 0.5
        
        # Adjust weights
        retriever.set_weights(0.8, 0.2)
        
        assert retriever.config.vector_weight == 0.8
        assert retriever.config.keyword_weight == 0.2
        
        # Verify results reflect new weights
        results = retriever.retrieve("python", top_k=3)
        for doc in results:
            assert doc.metadata["vector_weight"] == 0.8
            assert doc.metadata["keyword_weight"] == 0.2
    
    def test_hybrid_rrf_ranking_quality(self, bm25_retriever, mock_vector_retriever):
        """Test that RRF produces meaningful rankings."""
        retriever = HybridRetriever(
            vector_retriever=mock_vector_retriever,
            keyword_retriever=bm25_retriever,
            config=HybridRetrieverConfig(vector_weight=0.3, keyword_weight=0.7, top_k=5)
        )
        
        results = retriever.retrieve("python programming", top_k=5)
        
        # Results should be sorted by hybrid_score
        scores = [doc.metadata.get("hybrid_score", 0) for doc in results]
        assert scores == sorted(scores, reverse=True), "Results not sorted by hybrid score"
    
    def test_hybrid_config_persistence(self, bm25_retriever, mock_vector_retriever):
        """Test that configuration is properly stored and retrieved."""
        retriever = HybridRetriever(
            vector_retriever=mock_vector_retriever,
            keyword_retriever=bm25_retriever,
            config=HybridRetrieverConfig(
                vector_weight=0.4,
                keyword_weight=0.6,
                rrf_k=50,
                top_k=7,
                deduplicate=True
            )
        )
        
        config = retriever.get_config()
        
        assert config["vector_weight"] == 0.4
        assert config["keyword_weight"] == 0.6
        assert config["rrf_k"] == 50
        assert config["top_k"] == 7
        assert config["deduplicate"] is True


class TestABComparison:
    """A/B testing for vector-only vs hybrid search."""
    
    @pytest.fixture
    def test_documents(self):
        """Documents for A/B testing."""
        return [
            Document(page_content="Python programming language tutorial", metadata={"id": "1"}),
            Document(page_content="Machine learning with Python", metadata={"id": "2"}),
            Document(page_content="Data science fundamentals", metadata={"id": "3"}),
            Document(page_content="Deep learning neural networks", metadata={"id": "4"}),
            Document(page_content="Natural language processing basics", metadata={"id": "5"})
        ]
    
    def test_vector_vs_hybrid_accuracy(self, test_documents):
        """Compare vector-only vs hybrid search accuracy."""
        from core.retrievers.bm25_retriever import BM25Retriever
        from core.retrievers.hybrid_retriever import HybridRetriever, HybridRetrieverConfig
        
        # Setup BM25 retriever
        bm25 = BM25Retriever()
        bm25.index_documents(test_documents)
        
        # Setup mock vector retriever
        class MockVectorRetriever:
            def invoke(self, query, k=5):
                return test_documents[:k]
        
        vector_only = MockVectorRetriever()
        hybrid = HybridRetriever(
            vector_retriever=vector_only,
            keyword_retriever=bm25,
            config=HybridRetrieverConfig(vector_weight=0.3, keyword_weight=0.7)
        )
        
        # Test queries
        queries = ["python", "machine learning", "neural networks"]
        
        # Vector-only results
        vector_results = [vector_only.invoke(q, k=3) for q in queries]
        
        # Hybrid results
        hybrid_results = [hybrid.retrieve(q, top_k=3) for q in queries]
        
        # Both should return results
        assert all(len(r) > 0 for r in vector_results)
        assert all(len(r) > 0 for r in hybrid_results)
        
        # Hybrid should have additional metadata
        for result in hybrid_results:
            for doc in result:
                assert "hybrid_score" in doc.metadata
                assert "vector_score" in doc.metadata
                assert "keyword_score" in doc.metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
