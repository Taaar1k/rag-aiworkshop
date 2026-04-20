"""
Integration tests for Graph RAG components.

Tests cover:
- End-to-end graph retrieval
- Hybrid graph + vector search
- Integration with existing RAG components
- Performance benchmarks
"""

import pytest
from pathlib import Path

from langchain_core.documents import Document
from graph.graph_retriever import GraphRetriever, GraphRetrieverConfig
from graph.entity_extractor import EntityExtractor
from graph.hybrid_graph_retriever import HybridGraphRetriever, HybridGraphRetrieverConfig


class TestGraphRetrieverIntegration:
    """Integration tests for GraphRetriever."""
    
    def test_graph_retriever_with_mock(self):
        """Test graph retriever with mocked Neo4j connection."""
        config = GraphRetrieverConfig(
            neo4j_uri="bolt://localhost:7687",
            use_caching=False
        )
        retriever = GraphRetriever(config=config)
        
        # Test entity extraction (works without Neo4j)
        query = "What is the relationship between Apple and Microsoft?"
        entities = retriever._extract_entities(query)
        
        assert len(entities) > 0
        assert any("Apple" in e["name"] for e in entities)
        assert any("Microsoft" in e["name"] for e in entities)
    
    def test_graph_retriever_performance(self):
        """Test graph retriever performance metrics."""
        config = GraphRetrieverConfig(use_caching=False)
        retriever = GraphRetriever(config=config)
        
        # Simulate some retrievals
        for i in range(5):
            retriever._track_latency(50.0 + i * 10)
        
        stats = retriever.get_performance_stats()
        
        assert stats["avg_latency_ms"] == pytest.approx(70.0, rel=0.01)
        assert stats["max_latency_ms"] == 90.0
        assert stats["min_latency_ms"] == 50.0


class TestEntityExtractorIntegration:
    """Integration tests for EntityExtractor."""
    
    def test_entity_extraction_pipeline(self):
        """Test complete entity extraction pipeline."""
        extractor = EntityExtractor()
        
        text = """
        Apple Inc. was founded by Steve Jobs, Steve Wozniak, and Ronald Wayne in 1976.
        The company is headquartered in Cupertino, California.
        """
        
        entities = extractor.extract_entities(text)
        relationships = extractor.extract_relationships(text, entities)
        
        # Should extract multiple entities
        assert len(entities) > 0
        
        # Check entity types
        entity_types = [e.entity_type for e in entities]
        assert any(t in entity_types for t in ["PERSON", "ORGANIZATION", "LOCATION", "DATE"])
    
    def test_relationship_extraction(self):
        """Test relationship extraction from text."""
        extractor = EntityExtractor()
        
        text = "Apple was founded by Steve Jobs in 1976."
        relationships = extractor.extract_relationships(text)
        
        # May find relationships depending on patterns
        assert isinstance(relationships, list)


class TestHybridGraphRetrieverIntegration:
    """Integration tests for HybridGraphRetriever."""
    
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
    
    def test_hybrid_retriever_initialization(self, mock_vector_retriever):
        """Test hybrid retriever initialization."""
        config = GraphRetrieverConfig(use_caching=False)
        graph_retriever = GraphRetriever(config=config)
        
        hybrid_config = HybridGraphRetrieverConfig(
            vector_weight=0.6,
            graph_weight=0.4,
            top_k=10
        )
        
        retriever = HybridGraphRetriever(
            graph_retriever=graph_retriever,
            vector_retriever=mock_vector_retriever,
            config=hybrid_config
        )
        
        assert retriever.config.vector_weight == 0.6
        assert retriever.config.graph_weight == 0.4
        assert retriever.config.top_k == 10
    
    def test_hybrid_retriever_retrieve(self, mock_vector_retriever):
        """Test hybrid retrieval method."""
        config = GraphRetrieverConfig(use_caching=False)
        graph_retriever = GraphRetriever(config=config)
        
        hybrid_config = HybridGraphRetrieverConfig(
            vector_weight=0.5,
            graph_weight=0.5,
            top_k=5
        )
        
        retriever = HybridGraphRetriever(
            graph_retriever=graph_retriever,
            vector_retriever=mock_vector_retriever,
            config=hybrid_config
        )
        
        # This will use mock vector retriever and skip graph (no Neo4j)
        results = retriever.retrieve("test query", top_k=5)
        
        # Should return results from vector retriever
        assert isinstance(results, list)
        assert len(results) <= 5
        assert all(isinstance(r, Document) for r in results)
    
    def test_hybrid_retriever_weight_configuration(self, mock_vector_retriever):
        """Test weight configuration in hybrid retriever."""
        config = GraphRetrieverConfig(use_caching=False)
        graph_retriever = GraphRetriever(config=config)
        
        hybrid_config = HybridGraphRetrieverConfig(
            vector_weight=0.7,
            graph_weight=0.3
        )
        
        retriever = HybridGraphRetriever(
            graph_retriever=graph_retriever,
            vector_retriever=mock_vector_retriever,
            config=hybrid_config
        )
        
        assert retriever.config.vector_weight == 0.7
        assert retriever.config.graph_weight == 0.3
    
    def test_hybrid_retriever_set_weights(self, mock_vector_retriever):
        """Test dynamic weight setting."""
        config = GraphRetrieverConfig(use_caching=False)
        graph_retriever = GraphRetriever(config=config)
        
        hybrid_config = HybridGraphRetrieverConfig()
        retriever = HybridGraphRetriever(
            graph_retriever=graph_retriever,
            vector_retriever=mock_vector_retriever,
            config=hybrid_config
        )
        
        retriever.set_weights(0.8, 0.2)
        
        assert retriever.config.vector_weight == 0.8
        assert retriever.config.graph_weight == 0.2
    
    def test_hybrid_retriever_performance_stats(self, mock_vector_retriever):
        """Test performance statistics in hybrid retriever."""
        config = GraphRetrieverConfig(use_caching=False)
        graph_retriever = GraphRetriever(config=config)
        
        hybrid_config = HybridGraphRetrieverConfig()
        retriever = HybridGraphRetriever(
            graph_retriever=graph_retriever,
            vector_retriever=mock_vector_retriever,
            config=hybrid_config
        )
        
        # Execute some retrievals
        for _ in range(3):
            retriever.retrieve("test query")
        
        stats = retriever.get_performance_stats()
        
        assert "latency_samples" in stats
        assert "avg_latency_ms" in stats


class TestEndToEndIntegration:
    """End-to-end integration tests."""
    
    def test_full_pipeline(self):
        """Test complete graph RAG pipeline."""
        # Initialize components
        extractor = EntityExtractor()
        config = GraphRetrieverConfig(use_caching=False)
        graph_retriever = GraphRetriever(config=config)
        
        # Mock vector retriever
        class MockVectorRetriever:
            def invoke(self, query, k=5):
                return [
                    Document(
                        page_content=f"Result for {query}",
                        metadata={"id": "1", "score": 0.9}
                    )
                ]
        
        hybrid_config = HybridGraphRetrieverConfig()
        hybrid_retriever = HybridGraphRetriever(
            graph_retriever=graph_retriever,
            vector_retriever=MockVectorRetriever(),
            config=hybrid_config
        )
        
        # Test full pipeline
        query = "What is the relationship between Apple and Microsoft?"
        
        # Extract entities
        entities = extractor.extract_entities(query)
        assert len(entities) > 0
        
        # Hybrid retrieval
        results = hybrid_retriever.retrieve(query, top_k=5)
        assert len(results) > 0
    
    def test_document_conversion(self):
        """Test conversion of graph results to documents."""
        config = GraphRetrieverConfig(use_caching=False)
        graph_retriever = GraphRetriever(config=config)
        
        # Test document ID extraction
        doc = Document(
            page_content="Test content",
            metadata={"id": "test-id"}
        )
        
        doc_id = graph_retriever._get_doc_id(doc)
        assert doc_id == "test-id"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
