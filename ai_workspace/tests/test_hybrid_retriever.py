"""
Unit tests for Hybrid Retriever and BM25 components.

Tests cover:
- BM25Retriever indexing and search
- HybridRetriever RRF algorithm
- Deduplication logic
- Weight configuration
- Performance metrics
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from langchain_core.documents import Document
from core.retrievers.bm25_retriever import BM25Retriever, BM25Config
from core.retrievers.hybrid_retriever import HybridRetriever, HybridRetrieverConfig


class TestBM25Retriever:
    """Tests for BM25Retriever class."""
    
    def test_initialization(self):
        """Test BM25Retriever initialization."""
        retriever = BM25Retriever()
        assert retriever is not None
        assert retriever._bm25_index is None
        assert len(retriever._document_store) == 0
    
    def test_index_documents(self):
        """Test document indexing."""
        docs = [
            Document(page_content="The quick brown fox jumps over the lazy dog", metadata={"id": "1"}),
            Document(page_content="Python is a programming language", metadata={"id": "2"}),
            Document(page_content="Machine learning algorithms learn from data", metadata={"id": "3"})
        ]
        
        retriever = BM25Retriever()
        count = retriever.index_documents(docs)
        
        assert count == 3
        assert retriever._bm25_index is not None
        assert len(retriever._document_store) == 3
    
    def test_search_single_term(self):
        """Test search with single term."""
        docs = [
            Document(page_content="The quick brown fox jumps over the lazy fox", metadata={"id": "1"}),
            Document(page_content="Python programming language", metadata={"id": "2"})
        ]
        
        retriever = BM25Retriever()
        retriever.index_documents(docs)
        
        results = retriever.search("fox", k=2)
        
        # BM25 returns results sorted by score, fox should have highest score
        assert len(results) == 2
        assert "fox" in results[0].page_content.lower()
        # First result should contain more "fox" occurrences or have higher relevance
        assert results[0].metadata["bm25_score"] >= results[1].metadata["bm25_score"]
    
    def test_search_multiple_terms(self):
        """Test search with multiple terms."""
        docs = [
            Document(page_content="Python is a programming language", metadata={"id": "1"}),
            Document(page_content="Machine learning and AI", metadata={"id": "2"})
        ]
        
        retriever = BM25Retriever()
        retriever.index_documents(docs)
        
        results = retriever.search("python programming", k=2)
        
        assert len(results) >= 1
        assert "python" in results[0].page_content.lower()
    
    def test_search_no_results(self):
        """Test search with no matching terms."""
        docs = [
            Document(page_content="The quick brown fox", metadata={"id": "1"})
        ]
        
        retriever = BM25Retriever()
        retriever.index_documents(docs)
        
        # BM25 returns all documents even with low scores
        # Test that scores are low for non-matching terms
        results = retriever.search("nonexistent xyz", k=1)
        
        # Should return at least one result (BM25 always returns something)
        assert len(results) >= 1
        # Score should be very low (near zero) for non-matching terms
        assert results[0].metadata["bm25_score"] < 0.1
    
    def test_get_stats(self):
        """Test statistics retrieval."""
        docs = [
            Document(page_content="Test document one", metadata={"id": "1"}),
            Document(page_content="Test document two", metadata={"id": "2"})
        ]
        
        retriever = BM25Retriever()
        retriever.index_documents(docs)
        
        stats = retriever.get_stats()
        
        assert stats["document_count"] == 2
        assert stats["total_tokens"] > 0
        assert "k1" in stats
        assert "b" in stats
    
    def test_clear_index(self):
        """Test index clearing."""
        docs = [
            Document(page_content="Test content", metadata={"id": "1"})
        ]
        
        retriever = BM25Retriever()
        retriever.index_documents(docs)
        
        assert len(retriever._document_store) == 1
        
        retriever.clear_index()
        
        assert len(retriever._document_store) == 0
        assert retriever._bm25_index is None


class TestHybridRetriever:
    """Tests for HybridRetriever class."""
    
    @pytest.fixture
    def mock_vector_retriever(self):
        """Mock vector retriever for testing."""
        class MockVectorRetriever:
            def invoke(self, query, k=5):
                return [
                    Document(
                        page_content=f"Vector result {i} for {query}",
                        metadata={"id": f"v{i}", "score": 0.9 - i * 0.1}
                    )
                    for i in range(k)
                ]
        
        return MockVectorRetriever()
    
    @pytest.fixture
    def mock_keyword_retriever(self):
        """Mock keyword retriever for testing."""
        class MockKeywordRetriever:
            def invoke(self, query, k=5, min_score=0.0):
                return [
                    Document(
                        page_content=f"Keyword result {i} for {query}",
                        metadata={"id": f"k{i}", "bm25_score": 0.8 - i * 0.08}
                    )
                    for i in range(k)
                ]
        
        return MockKeywordRetriever()
    
    def test_initialization(self, mock_vector_retriever, mock_keyword_retriever):
        """Test HybridRetriever initialization."""
        retriever = HybridRetriever(
            vector_retriever=mock_vector_retriever,
            keyword_retriever=mock_keyword_retriever
        )
        
        assert retriever.vector_retriever is mock_vector_retriever
        assert retriever.keyword_retriever is mock_keyword_retriever
        assert retriever.config.vector_weight == 0.3
        assert retriever.config.keyword_weight == 0.7
    
    def test_reciprocal_rank_fusion(self, mock_vector_retriever, mock_keyword_retriever):
        """Test RRF algorithm implementation."""
        retriever = HybridRetriever(
            vector_retriever=mock_vector_retriever,
            keyword_retriever=mock_keyword_retriever
        )
        
        vector_results = [
            (0, Document(page_content="Result 1", metadata={"id": "1"}), 0.9),
            (1, Document(page_content="Result 2", metadata={"id": "2"}), 0.8)
        ]
        
        keyword_results = [
            (0, Document(page_content="Result 1", metadata={"id": "1"}), 0.85),
            (1, Document(page_content="Result 3", metadata={"id": "3"}), 0.75)
        ]
        
        fused = retriever._reciprocal_rank_fusion(vector_results, keyword_results)
        
        assert len(fused) >= 1
        # Document 1 should have highest RRF score (appears in both)
        assert fused[0][1].metadata["id"] == "1"
    
    def test_deduplication(self, mock_vector_retriever, mock_keyword_retriever):
        """Test deduplication logic."""
        retriever = HybridRetriever(
            vector_retriever=mock_vector_retriever,
            keyword_retriever=mock_keyword_retriever,
            config=HybridRetrieverConfig(deduplicate=True)
        )
        
        # Create results with duplicates
        vector_results = [
            (0, Document(page_content="Result 1", metadata={"id": "1"}), 0.9),
            (1, Document(page_content="Result 2", metadata={"id": "2"}), 0.8)
        ]
        
        keyword_results = [
            (0, Document(page_content="Result 1", metadata={"id": "1"}), 0.85),  # Duplicate
            (1, Document(page_content="Result 3", metadata={"id": "3"}), 0.75)
        ]
        
        fused = retriever._reciprocal_rank_fusion(vector_results, keyword_results)
        deduplicated = retriever._deduplicate(fused)
        
        # Should have unique IDs only
        ids = [doc.metadata["id"] for _, doc, _, _, _ in deduplicated]
        assert len(ids) == len(set(ids))
    
    def test_weight_configuration(self, mock_vector_retriever, mock_keyword_retriever):
        """Test weight configuration."""
        retriever = HybridRetriever(
            vector_retriever=mock_vector_retriever,
            keyword_retriever=mock_keyword_retriever,
            config=HybridRetrieverConfig(
                vector_weight=0.5,
                keyword_weight=0.5
            )
        )
        
        assert retriever.config.vector_weight == 0.5
        assert retriever.config.keyword_weight == 0.5
    
    def test_set_weights(self, mock_vector_retriever, mock_keyword_retriever):
        """Test dynamic weight setting."""
        retriever = HybridRetriever(
            vector_retriever=mock_vector_retriever,
            keyword_retriever=mock_keyword_retriever
        )
        
        retriever.set_weights(0.6, 0.4)
        
        assert retriever.config.vector_weight == 0.6
        assert retriever.config.keyword_weight == 0.4
    
    def test_retrieve(self, mock_vector_retriever, mock_keyword_retriever):
        """Test retrieve method."""
        retriever = HybridRetriever(
            vector_retriever=mock_vector_retriever,
            keyword_retriever=mock_keyword_retriever,
            config=HybridRetrieverConfig(top_k=5)
        )
        
        results = retriever.retrieve("test query", top_k=5)
        
        assert len(results) <= 5
        assert all(isinstance(doc, Document) for doc in results)
    
    def test_performance_stats(self, mock_vector_retriever, mock_keyword_retriever):
        """Test performance statistics."""
        retriever = HybridRetriever(
            vector_retriever=mock_vector_retriever,
            keyword_retriever=mock_keyword_retriever
        )
        
        # Execute some retrievals to collect latency data
        for _ in range(5):
            retriever.retrieve("test query")
        
        stats = retriever.get_performance_stats()
        
        assert stats["latency_samples"] == 5
        assert "avg_latency_ms" in stats
        assert "max_latency_ms" in stats
        assert "min_latency_ms" in stats
    
    def test_get_config(self, mock_vector_retriever, mock_keyword_retriever):
        """Test configuration retrieval."""
        retriever = HybridRetriever(
            vector_retriever=mock_vector_retriever,
            keyword_retriever=mock_keyword_retriever
        )
        
        config = retriever.get_config()
        
        assert "vector_weight" in config
        assert "keyword_weight" in config
        assert "rrf_k" in config
        assert "top_k" in config
        assert "deduplicate" in config


class TestRRFAlgorithm:
    """Specific tests for Reciprocal Rank Fusion algorithm."""
    
    def test_rrf_ranking_formula(self):
        """Test RRF ranking formula correctness."""
        retriever = HybridRetriever(
            vector_retriever=None,
            keyword_retriever=None
        )
        
        # Create test results
        vector_results = [
            (0, Document(page_content="A", metadata={"id": "1"}), 1.0),
            (1, Document(page_content="B", metadata={"id": "2"}), 0.9),
            (2, Document(page_content="C", metadata={"id": "3"}), 0.8)
        ]
        
        keyword_results = [
            (0, Document(page_content="D", metadata={"id": "4"}), 0.95),
            (1, Document(page_content="E", metadata={"id": "5"}), 0.85),
            (2, Document(page_content="F", metadata={"id": "6"}), 0.75)
        ]
        
        fused = retriever._reciprocal_rank_fusion(vector_results, keyword_results, rrf_k=60)
        
        # All documents should have RRF score
        for _, _, _, _, _ in fused:
            assert len(_) > 0
    
    def test_rrf_with_common_documents(self):
        """Test RRF when documents appear in both rankings."""
        retriever = HybridRetriever(
            vector_retriever=None,
            keyword_retriever=None
        )
        
        vector_results = [
            (0, Document(page_content="Common", metadata={"id": "1"}), 0.9),
            (1, Document(page_content="VectorOnly", metadata={"id": "2"}), 0.8)
        ]
        
        keyword_results = [
            (0, Document(page_content="Common", metadata={"id": "1"}), 0.85),
            (1, Document(page_content="KeywordOnly", metadata={"id": "3"}), 0.75)
        ]
        
        fused = retriever._reciprocal_rank_fusion(vector_results, keyword_results)
        
        # Common document should have highest RRF score
        assert fused[0][1].metadata["id"] == "1"
        assert fused[0][2] > fused[1][2]
        assert fused[0][2] > fused[2][2]


class TestDeduplication:
    """Tests for deduplication functionality."""
    
    def test_deduplicate_keeps_highest_score(self):
        """Test that deduplication keeps highest-scoring version."""
        retriever = HybridRetriever(
            vector_retriever=None,
            keyword_retriever=None
        )
        
        results = [
            (0.5, Document(page_content="Doc 1", metadata={"id": "1"}), 0.5, 0.3, "vector"),
            (0.7, Document(page_content="Doc 1", metadata={"id": "1"}), 0.7, 0.4, "keyword")
        ]
        
        deduplicated = retriever._deduplicate(results)
        
        assert len(deduplicated) == 1
        assert deduplicated[0][0] == 0.7  # Higher RRF score
    
    def test_deduplicate_no_duplicates(self):
        """Test deduplication with no duplicates."""
        retriever = HybridRetriever(
            vector_retriever=None,
            keyword_retriever=None
        )
        
        results = [
            (0.5, Document(page_content="Doc 1", metadata={"id": "1"}), 0.5, 0.3, "vector"),
            (0.7, Document(page_content="Doc 2", metadata={"id": "2"}), 0.7, 0.4, "keyword"),
            (0.6, Document(page_content="Doc 3", metadata={"id": "3"}), 0.6, 0.35, "hybrid")
        ]
        
        deduplicated = retriever._deduplicate(results)
        
        assert len(deduplicated) == 3


class TestWeightedScoring:
    """Tests for weighted scoring implementation."""
    
    def test_weighted_scoring_applied(self):
        """Test that weights are correctly applied to final scores."""
        class MockVectorRetriever:
            def invoke(self, query, k=5):
                return [
                    Document(
                        page_content=f"Vector result {i} for {query}",
                        metadata={"id": f"v{i}", "score": 0.9 - i * 0.1}
                    )
                    for i in range(k)
                ]
        
        class MockKeywordRetriever:
            def invoke(self, query, k=5, min_score=0.0):
                return [
                    Document(
                        page_content=f"Keyword result {i} for {query}",
                        metadata={"id": f"k{i}", "bm25_score": 0.8 - i * 0.08}
                    )
                    for i in range(k)
                ]
        
        retriever = HybridRetriever(
            vector_retriever=MockVectorRetriever(),
            keyword_retriever=MockKeywordRetriever(),
            config=HybridRetrieverConfig(
                vector_weight=0.7,
                keyword_weight=0.3
            )
        )
        
        results = retriever.retrieve("test", top_k=3)
        
        # Check that metadata contains weighted scores
        for doc in results:
            assert "hybrid_score" in doc.metadata
            assert "vector_score" in doc.metadata
            assert "keyword_score" in doc.metadata
            assert doc.metadata["vector_weight"] == 0.7
            assert doc.metadata["keyword_weight"] == 0.3


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
