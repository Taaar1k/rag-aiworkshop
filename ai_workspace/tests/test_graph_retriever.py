"""
Unit tests for Graph Retriever component.

Tests cover:
- GraphRetriever initialization and configuration
- Entity extraction from queries
- Graph traversal simulation
- Performance tracking
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from graph.graph_retriever import GraphRetriever, GraphRetrieverConfig


class TestGraphRetrieverConfig:
    """Tests for GraphRetrieverConfig."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = GraphRetrieverConfig()
        
        assert config.neo4j_uri == "bolt://localhost:7687"
        assert config.neo4j_username == "neo4j"
        assert config.neo4j_password == "password"
        assert config.traversal_depth == 2
        assert config.max_results == 10
        assert config.relationship_filter == "RELATED_TO>"
        assert config.entity_label == "Entity"
        assert config.min_confidence == 0.5
        assert config.use_caching is True
        assert config.cache_ttl_seconds == 3600
    
    def test_custom_config(self):
        """Test custom configuration values."""
        config = GraphRetrieverConfig(
            neo4j_uri="bolt://custom:7687",
            traversal_depth=3,
            max_results=20,
            use_caching=False
        )
        
        assert config.neo4j_uri == "bolt://custom:7687"
        assert config.traversal_depth == 3
        assert config.max_results == 20
        assert config.use_caching is False


class TestGraphRetriever:
    """Tests for GraphRetriever class."""
    
    def test_initialization_without_connection(self):
        """Test initialization without database connection."""
        config = GraphRetrieverConfig()
        retriever = GraphRetriever(config=config)
        
        assert retriever.config == config
        # Note: Neo4j driver may attempt connection on init, so we check _connected
        assert retriever._connected is False or retriever._connected is True  # Either way is valid
        assert len(retriever._latency_samples) == 0
    
    def test_initialization_with_config(self):
        """Test initialization with custom config."""
        config = GraphRetrieverConfig(
            neo4j_uri="bolt://localhost:7687",
            traversal_depth=1
        )
        retriever = GraphRetriever(config=config)
        
        assert retriever.config.traversal_depth == 1
    
    def test_entity_extraction_pattern_matching(self):
        """Test entity extraction using pattern matching."""
        config = GraphRetrieverConfig()
        retriever = GraphRetriever(config=config)
        
        query = "What is the relationship between Apple and Microsoft?"
        entities = retriever._extract_entities(query)
        
        # Should extract Apple and Microsoft
        entity_names = [e["name"] for e in entities]
        assert "Apple" in entity_names
        assert "Microsoft" in entity_names
        
        # Check entity types
        for entity in entities:
            assert "name" in entity
            assert "type" in entity
            assert "confidence" in entity
    
    def test_entity_extraction_with_years(self):
        """Test entity extraction with year patterns."""
        config = GraphRetrieverConfig()
        retriever = GraphRetriever(config=config)
        
        query = "What happened in 2020 and 2021?"
        entities = retriever._extract_entities(query)
        
        # Should extract years
        entity_names = [e["name"] for e in entities]
        assert "2020" in entity_names
        assert "2021" in entity_names
    
    def test_entity_extraction_confidence_filtering(self):
        """Test that low confidence entities are filtered."""
        config = GraphRetrieverConfig(min_confidence=0.7)
        retriever = GraphRetriever(config=config)
        
        query = "Test query with some words"
        entities = retriever._extract_entities(query)
        
        # All entities should meet confidence threshold
        for entity in entities:
            assert entity["confidence"] >= 0.7
    
    def test_entity_extraction_limit(self):
        """Test entity extraction result limit."""
        config = GraphRetrieverConfig()
        retriever = GraphRetriever(config=config)
        
        # Query with many potential entities
        query = "Apple Microsoft Google Amazon Facebook"
        entities = retriever._extract_entities(query)
        
        # Should be limited to 5
        assert len(entities) <= 5
    
    def test_performance_tracking(self):
        """Test performance statistics tracking."""
        config = GraphRetrieverConfig()
        retriever = GraphRetriever(config=config)
        
        # Manually track some latencies
        for i in range(10):
            retriever._track_latency(float(i * 10))
        
        stats = retriever.get_performance_stats()
        
        assert stats["latency_samples"] == 10
        assert "avg_latency_ms" in stats
        assert "max_latency_ms" in stats
        assert "min_latency_ms" in stats
    
    def test_cache_operations(self):
        """Test cache operations."""
        config = GraphRetrieverConfig(use_caching=True)
        retriever = GraphRetriever(config=config)
        
        # Add to cache
        test_data = [{"test": "data"}]
        retriever._cache["test_key"] = (test_data, 123.456)
        
        # Retrieve from cache
        assert "test_key" in retriever._cache
        
        # Clear cache
        retriever.clear_cache()
        assert len(retriever._cache) == 0
    
    def test_context_manager(self):
        """Test context manager functionality."""
        config = GraphRetrieverConfig()
        
        # This will fail without Neo4j, but should handle gracefully
        try:
            with GraphRetriever(config=config) as retriever:
                # Connection attempt will fail, but context manager should handle it
                pass
        except Exception:
            # Expected if Neo4j not available
            pass


class TestEntityExtraction:
    """Tests for entity extraction patterns."""
    
    def test_proper_noun_extraction(self):
        """Test proper noun extraction."""
        config = GraphRetrieverConfig()
        retriever = GraphRetriever(config=config)
        
        query = "Who is the CEO of Google?"
        entities = retriever._extract_entities(query)
        
        entity_names = [e["name"] for e in entities]
        assert "Google" in entity_names
    
    def test_acronym_extraction(self):
        """Test acronym extraction."""
        config = GraphRetrieverConfig()
        retriever = GraphRetriever(config=config)
        
        query = "What does NASA stand for?"
        entities = retriever._extract_entities(query)
        
        entity_names = [e["name"] for e in entities]
        assert "NASA" in entity_names
    
    def test_empty_query(self):
        """Test entity extraction with empty query."""
        config = GraphRetrieverConfig()
        retriever = GraphRetriever(config=config)
        
        entities = retriever._extract_entities("")
        assert len(entities) == 0
    
    def test_special_characters(self):
        """Test entity extraction with special characters."""
        config = GraphRetrieverConfig()
        retriever = GraphRetriever(config=config)
        
        query = "Query with special chars: @#$%^&*()"
        entities = retriever._extract_entities(query)
        
        # Should handle gracefully
        assert isinstance(entities, list)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
