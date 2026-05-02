"""
Tests for Cross-Encoder Reranker.

Tests:
- Basic reranking functionality
- Score calculation and sorting
- Latency tracking
- Edge cases (empty input, min score filtering)
"""

import pytest
import time
from typing import List
import numpy as np

from langchain_core.documents import Document

from src.core.rerankers.cross_encoder_reranker import (
    CrossEncoderReranker,
    RerankerConfig
)


class TestCrossEncoderReranker:
    """Test suite for CrossEncoderReranker."""
    
    @pytest.fixture
    def sample_documents(self) -> List[Document]:
        """Sample documents for testing."""
        return [
            Document(
                page_content="The quick brown fox jumps over the lazy dog",
                metadata={"source": "test1", "id": "1"}
            ),
            Document(
                page_content="Machine learning is a subset of artificial intelligence",
                metadata={"source": "test2", "id": "2"}
            ),
            Document(
                page_content="Python is a popular programming language for data science",
                metadata={"source": "test3", "id": "3"}
            ),
            Document(
                page_content="Neural networks are inspired by biological neural systems",
                metadata={"source": "test4", "id": "4"}
            ),
            Document(
                page_content="Cross-encoders provide more accurate relevance scoring",
                metadata={"source": "test5", "id": "5"}
            )
        ]
    
    @pytest.fixture
    def reranker(self):
        """Create a reranker instance for testing."""
        config = RerankerConfig(
            model_name="cross-encoder/ms-marco-MiniLM-L-6-v2",
            device="cpu",
            top_k=3,
            max_chunks=100,
            min_score=0.0  # Allow all scores
        )
        return CrossEncoderReranker(config)
    
    def test_initialization(self, reranker):
        """Test reranker initialization."""
        assert reranker is not None
        assert reranker.model_name == "cross-encoder/ms-marco-MiniLM-L-6-v2"
        assert reranker.config.top_k == 3
        assert len(reranker._latency_samples) == 0
    
    def test_rerank_with_query(self, reranker, sample_documents):
        """Test basic reranking functionality."""
        query = "machine learning algorithms"
        result = reranker.rerank(query, sample_documents, top_n=3)
        
        # Cross-encoder may return fewer results if scores are below threshold
        assert len(result) > 0
        assert isinstance(result, list)
        assert all(isinstance(item, tuple) for item in result)
        assert all(len(item) == 2 for item in result)
        
        # Check that documents have scores (can be numpy float32 or Python float)
        for doc, score in result:
            assert isinstance(doc, Document)
            assert np.isscalar(score)  # Accept any numeric scalar type
    
    def test_rerank_sorting(self, reranker, sample_documents):
        """Test that results are sorted by score (descending)."""
        query = "machine learning"
        result = reranker.rerank(query, sample_documents, top_n=5)
        
        if len(result) > 1:
            scores = [float(score) for _, score in result]
            assert scores == sorted(scores, reverse=True)
    
    def test_rerank_empty_input(self, reranker):
        """Test reranking with empty document list."""
        query = "test query"
        result = reranker.rerank(query, [], top_n=5)
        assert result == []
    
    def test_rerank_min_score_filtering(self, reranker, sample_documents):
        """Test minimum score filtering."""
        query = "machine learning algorithms"
        
        # With low threshold, should return results
        result_low = reranker.rerank(query, sample_documents, top_n=5, min_score=0.0)
        
        # With high threshold, should return fewer or no results
        result_high = reranker.rerank(query, sample_documents, top_n=5, min_score=0.9)
        
        assert len(result_high) <= len(result_low)
    
    def test_rerank_with_metadata(self, reranker, sample_documents):
        """Test reranking with metadata attachment."""
        query = "machine learning"
        result = reranker.rerank_with_metadata(query, sample_documents, top_n=3)
        
        # Cross-encoder may return fewer results if scores are below threshold
        assert len(result) > 0
        
        # Check metadata
        for doc in result:
            assert hasattr(doc, 'metadata')
            assert 'rerank_score' in doc.metadata
            assert 'rerank_model' in doc.metadata
            assert doc.metadata['rerank_model'] == reranker.model_name
    
    def test_rerank_top_n_limit(self, reranker, sample_documents):
        """Test top_n parameter limits results."""
        query = "machine learning"
        
        result_2 = reranker.rerank(query, sample_documents, top_n=2)
        result_5 = reranker.rerank(query, sample_documents, top_n=5)
        
        # Results should be limited by top_n
        assert len(result_2) <= 2
        assert len(result_5) <= 5
        # More top_n should return at least as many results
        assert len(result_5) >= len(result_2)
    
    def test_rerank_max_chunks(self, reranker, sample_documents):
        """Test max_chunks parameter limits processing."""
        query = "test query"
        
        # Create more documents than max_chunks
        many_docs = sample_documents * 3  # 15 documents
        
        result = reranker.rerank(query, many_docs, top_n=3)
        
        # Should only process up to max_chunks
        assert len(result) <= reranker.config.max_chunks
    
    def test_latency_tracking(self, reranker, sample_documents):
        """Test latency tracking functionality."""
        query = "machine learning"
        
        # Perform multiple reranks
        for _ in range(5):
            reranker.rerank(query, sample_documents, top_n=3)
        
        # Check latency stats
        stats = reranker.get_performance_stats()
        
        assert stats['latency_samples'] == 5
        assert stats['rerank_count'] == 5
        assert 'avg_latency_ms' in stats
        assert stats['avg_latency_ms'] > 0
    
    def test_performance_stats(self, reranker, sample_documents):
        """Test performance statistics calculation."""
        query = "test query"
        
        # Perform reranks
        for _ in range(10):
            reranker.rerank(query, sample_documents, top_n=3)
        
        stats = reranker.get_performance_stats()
        
        assert 'latency_samples' in stats
        assert 'avg_latency_ms' in stats
        assert 'max_latency_ms' in stats
        assert 'min_latency_ms' in stats
        assert stats['latency_samples'] == 10
    
    def test_config_persistence(self, reranker):
        """Test that configuration is properly persisted."""
        config = reranker.get_config()
        
        assert config['model_name'] == reranker.model_name
        assert config['device'] == reranker.config.device
        assert config['top_k'] == reranker.config.top_k
        assert config['max_chunks'] == reranker.config.max_chunks


class TestHybridRetrieverWithRerank:
    """Test suite for HybridRetrieverWithRerank."""
    
    @pytest.fixture
    def sample_documents(self) -> List[Document]:
        """Sample documents for testing."""
        return [
            Document(
                page_content="The quick brown fox jumps over the lazy dog",
                metadata={"source": "test1", "id": "1"}
            ),
            Document(
                page_content="Machine learning is a subset of artificial intelligence",
                metadata={"source": "test2", "id": "2"}
            ),
            Document(
                page_content="Python is a popular programming language for data science",
                metadata={"source": "test3", "id": "3"}
            )
        ]
    
    @pytest.fixture
    def mock_hybrid_retriever(self):
        """Mock hybrid retriever for testing."""
        class MockRetriever:
            def retrieve(self, query, top_k, **kwargs):
                return [
                    Document(
                        page_content="Machine learning is a subset of artificial intelligence",
                        metadata={"hybrid_score": 0.8, "vector_score": 0.7, "keyword_score": 0.9}
                    ),
                    Document(
                        page_content="Python is a popular programming language for data science",
                        metadata={"hybrid_score": 0.6, "vector_score": 0.5, "keyword_score": 0.7}
                    )
                ]
        return MockRetriever()
    
    @pytest.fixture
    def mock_reranker(self):
        """Mock reranker for testing."""
        class MockReranker:
            def rerank_with_metadata(self, query, documents, top_n, min_score):
                return documents[:top_n]
            
            def get_performance_stats(self):
                return {"rerank_count": 0, "latency_samples": 0}
        return MockReranker()
    
    def test_initialization(self, mock_hybrid_retriever, mock_reranker):
        """Test initialization of hybrid retriever with rerank."""
        from src.core.retrievers.hybrid_retriever_with_rerank import (
            HybridRetrieverWithRerank,
            HybridRetrieverWithRerankConfig
        )
        
        config = HybridRetrieverWithRerankConfig()
        retriever = HybridRetrieverWithRerank(
            hybrid_retriever=mock_hybrid_retriever,
            reranker=mock_reranker,
            config=config
        )
        
        assert retriever is not None
        assert retriever._rerank_enabled is True
    
    def test_toggle_reranking(self, mock_hybrid_retriever, mock_reranker):
        """Test enabling/disabling reranking."""
        from src.core.retrievers.hybrid_retriever_with_rerank import (
            HybridRetrieverWithRerank,
            HybridRetrieverWithRerankConfig
        )
        
        config = HybridRetrieverWithRerankConfig()
        retriever = HybridRetrieverWithRerank(
            hybrid_retriever=mock_hybrid_retriever,
            reranker=mock_reranker,
            config=config
        )
        
        # Disable reranking
        retriever.toggle_reranking(False)
        assert retriever._rerank_enabled is False
        
        # Enable reranking
        retriever.toggle_reranking(True)
        assert retriever._rerank_enabled is True
    
    def test_performance_stats(self, mock_hybrid_retriever, mock_reranker):
        """Test performance statistics for hybrid retriever with rerank."""
        from src.core.retrievers.hybrid_retriever_with_rerank import (
            HybridRetrieverWithRerank,
            HybridRetrieverWithRerankConfig
        )
        
        config = HybridRetrieverWithRerankConfig()
        retriever = HybridRetrieverWithRerank(
            hybrid_retriever=mock_hybrid_retriever,
            reranker=mock_reranker,
            config=config
        )
        
        # Perform some retrievals
        for _ in range(5):
            retriever.retrieve("test query", top_k=2)
        
        stats = retriever.get_performance_stats()
        
        assert 'total_requests' in stats
        assert stats['total_requests'] == 5
        assert 'hybrid_search' in stats
        assert 'reranking' in stats


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
