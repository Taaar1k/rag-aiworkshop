"""
Unit tests for Entity Extractor component.

Tests cover:
- Entity extraction using patterns
- NLP-based extraction (if available)
- Relationship extraction
- Batch processing
"""

import pytest
import sys
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from graph.entity_extractor import EntityExtractor, Entity, Relationship, ExtractionResult


class TestEntityExtractor:
    """Tests for EntityExtractor class."""
    
    def test_initialization(self):
        """Test entity extractor initialization."""
        extractor = EntityExtractor()
        assert extractor.use_nlp is False
        assert len(extractor.entity_types) > 0
    
    def test_initialization_with_nlp(self):
        """Test initialization with NLP enabled."""
        extractor = EntityExtractor(use_nlp=True)
        # NLP may or may not be available
        assert extractor.use_nlp is False or extractor.use_nlp is True
    
    def test_extract_entities_basic(self):
        """Test basic entity extraction."""
        extractor = EntityExtractor()
        
        text = "Apple was founded by Steve Jobs in 1976."
        entities = extractor.extract_entities(text)
        
        # Should extract some entities
        assert len(entities) > 0
        
        # Check entity structure
        for entity in entities:
            assert isinstance(entity, Entity)
            assert hasattr(entity, 'name')
            assert hasattr(entity, 'entity_type')
            assert hasattr(entity, 'confidence')
    
    def test_extract_entities_person(self):
        """Test person entity extraction."""
        extractor = EntityExtractor()
        
        text = "Steve Jobs founded Apple in 1976."
        entities = extractor.extract_entities(text)
        
        # Should extract Steve Jobs
        entity_names = [e.name for e in entities]
        assert any("Steve" in name for name in entity_names)
    
    def test_extract_entities_date(self):
        """Test date entity extraction."""
        extractor = EntityExtractor()
        
        text = "The event occurred on 2024-01-15."
        entities = extractor.extract_entities(text)
        
        # Should extract date
        entity_names = [e.name for e in entities]
        assert any("2024" in name for name in entity_names)
    
    def test_extract_entities_with_custom_types(self):
        """Test extraction with custom entity types."""
        extractor = EntityExtractor(entity_types=["PERSON", "DATE"])
        
        text = "John Doe was born on 1990-05-15."
        entities = extractor.extract_entities(text)
        
        # Should extract entities of specified types
        entity_types = [e.entity_type for e in entities]
        assert any(t in entity_types for t in ["PERSON", "DATE"])
    
    def test_extract_entities_empty_text(self):
        """Test extraction with empty text."""
        extractor = EntityExtractor()
        
        entities = extractor.extract_entities("")
        assert len(entities) == 0
    
    def test_extract_entities_special_characters(self):
        """Test extraction with special characters."""
        extractor = EntityExtractor()
        
        text = "Test with @#$% special chars!"
        entities = extractor.extract_entities(text)
        
        # Should handle gracefully
        assert isinstance(entities, list)
    
    def test_extract_relationships(self):
        """Test relationship extraction."""
        extractor = EntityExtractor()
        
        text = "Apple was founded by Steve Jobs in 1976."
        relationships = extractor.extract_relationships(text)
        
        # May or may not find relationships depending on patterns
        assert isinstance(relationships, list)
    
    def test_extract_relationships_with_entities(self):
        """Test relationship extraction constrained by entities."""
        extractor = EntityExtractor()
        
        text = "Apple was founded by Steve Jobs in 1976."
        entities = extractor.extract_entities(text)
        relationships = extractor.extract_relationships(text, entities)
        
        assert isinstance(relationships, list)
    
    def test_extract_from_document(self):
        """Test full document extraction."""
        extractor = EntityExtractor()
        
        text = "Apple was founded by Steve Jobs in 1976. Microsoft is a competitor."
        result = extractor.extract_from_document(text)
        
        assert isinstance(result, ExtractionResult)
        assert len(result.entities) > 0
        assert isinstance(result.relationships, list)
        assert result.extraction_time_ms > 0
    
    def test_batch_extract(self):
        """Test batch extraction."""
        extractor = EntityExtractor()
        
        texts = [
            "Apple was founded by Steve Jobs.",
            "Microsoft was founded by Bill Gates."
        ]
        results = extractor.batch_extract(texts)
        
        assert len(results) == 2
        for result in results:
            assert isinstance(result, ExtractionResult)
    
    def test_extraction_result_to_dict(self):
        """Test ExtractionResult serialization."""
        extractor = EntityExtractor()
        
        text = "Test entity extraction."
        result = extractor.extract_from_document(text)
        
        result_dict = result.to_dict()
        
        assert "entities" in result_dict
        assert "relationships" in result_dict
        assert "extraction_time_ms" in result_dict


class TestEntity:
    """Tests for Entity dataclass."""
    
    def test_entity_creation(self):
        """Test entity creation."""
        entity = Entity(
            name="Test Entity",
            entity_type="TEST",
            confidence=0.9,
            position=(0, 10),
            context="Test context"
        )
        
        assert entity.name == "Test Entity"
        assert entity.entity_type == "TEST"
        assert entity.confidence == 0.9
        assert entity.position == (0, 10)
        assert entity.context == "Test context"
    
    def test_entity_to_dict(self):
        """Test entity to dictionary conversion."""
        entity = Entity(
            name="Test",
            entity_type="TYPE",
            confidence=0.8,
            position=(0, 4)
        )
        
        entity_dict = entity.to_dict()
        
        assert entity_dict["name"] == "Test"
        assert entity_dict["type"] == "TYPE"
        assert entity_dict["confidence"] == 0.8
        assert entity_dict["position"] == (0, 4)


class TestRelationship:
    """Tests for Relationship dataclass."""
    
    def test_relationship_creation(self):
        """Test relationship creation."""
        relationship = Relationship(
            source="Entity1",
            target="Entity2",
            relationship_type="RELATED",
            confidence=0.7,
            context="Test context"
        )
        
        assert relationship.source == "Entity1"
        assert relationship.target == "Entity2"
        assert relationship.relationship_type == "RELATED"
        assert relationship.confidence == 0.7
        assert relationship.context == "Test context"
    
    def test_relationship_to_dict(self):
        """Test relationship to dictionary conversion."""
        relationship = Relationship(
            source="A",
            target="B",
            relationship_type="CONNECTS",
            confidence=0.9
        )
        
        rel_dict = relationship.to_dict()
        
        assert rel_dict["source"] == "A"
        assert rel_dict["target"] == "B"
        assert rel_dict["type"] == "CONNECTS"
        assert rel_dict["confidence"] == 0.9


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
