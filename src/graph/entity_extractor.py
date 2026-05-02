"""
Entity Extraction Pipeline for Graph RAG.

Extracts entities and relationships from documents using NLP techniques
and prepares them for graph database storage.
"""

import re
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from collections import defaultdict

try:
    from transformers import pipeline
    TRANSFORMERS_AVAILABLE = True
except ImportError:
    TRANSFORMERS_AVAILABLE = False
    print("Warning: transformers not available. Using basic entity extraction.")


@dataclass
class Entity:
    """Represents an extracted entity."""
    name: str
    entity_type: str
    confidence: float
    position: Tuple[int, int]  # Start and end positions in text
    context: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "type": self.entity_type,
            "confidence": self.confidence,
            "position": self.position,
            "context": self.context
        }


@dataclass
class Relationship:
    """Represents an extracted relationship."""
    source: str
    target: str
    relationship_type: str
    confidence: float
    context: str = ""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "source": self.source,
            "target": self.target,
            "type": self.relationship_type,
            "confidence": self.confidence,
            "context": self.context
        }


@dataclass
class ExtractionResult:
    """Result of entity and relationship extraction."""
    entities: List[Entity]
    relationships: List[Relationship]
    extraction_time_ms: float
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            "entities": [e.to_dict() for e in self.entities],
            "relationships": [r.to_dict() for r in self.relationships],
            "extraction_time_ms": self.extraction_time_ms
        }


class EntityExtractor:
    """
    Pipeline for extracting entities and relationships from text.
    
    Uses multiple strategies:
    - Pattern-based extraction (regex)
    - NLP-based extraction (NER if transformers available)
    - Heuristic-based relationship extraction
    
    Args:
        use_nlp: Whether to use transformers NLP models
        entity_types: List of entity types to extract
    """
    
    # Common entity type patterns
    ENTITY_PATTERNS = {
        "PERSON": r'\b[A-Z][a-z]+(?: [A-Z][a-z]+)*\b',
        "ORGANIZATION": r'\b[A-Z][A-Z0-9]+(?: [A-Z][A-Z0-9]+)*\b',
        "LOCATION": r'\b[A-Z][a-z]+(?: [A-Z][a-z]+)* (?:City|Country|State|Street|River|Mountain)\b',
        "DATE": r'\b(?:\d{4}[-/]\d{2}[-/]\d{2}|\d{1,2}[./]\d{1,2}[./]\d{2,4})\b',
        "NUMBER": r'\b\d+(?:\.\d+)?(?:\s*(?:million|billion|thousand|percent|%)?)?\b',
        "EMAIL": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
        "URL": r'https?://[^\s]+',
    }
    
    # Common relationship patterns
    RELATIONSHIP_PATTERNS = [
        (r'(\w+)\s+(?:is|are|was|were)\s+(?:the\s+)?(?:son|daughter|father|mother|brother|sister|husband|wife|child|parent|manager|employee|owner|creator)\s+of\s+(\w+)', "FAMILY"),
        (r'(\w+)\s+(?:works?|employs?|manages?)\s+(?:at|for)\s+(\w+)', "EMPLOYMENT"),
        (r'(\w+)\s+(?:located|based)\s+(?:in|at)\s+(\w+)', "LOCATION"),
        (r'(\w+)\s+(?:founded|created|established)\s+(?:in|by)\s+(\w+)', "CREATION"),
        (r'(\w+)\s+(?:owns?|possesses?|has)\s+(\w+)', "OWNERSHIP"),
        (r'(\w+)\s+(?:related|connected|associated)\s+with\s+(\w+)', "ASSOCIATION"),
    ]
    
    def __init__(
        self,
        use_nlp: bool = False,
        entity_types: Optional[List[str]] = None
    ):
        self.use_nlp = use_nlp and TRANSFORMERS_AVAILABLE
        self.entity_types = entity_types or list(self.ENTITY_PATTERNS.keys())
        
        # NLP pipeline if available
        self._nlp_pipeline = None
        if self.use_nlp:
            try:
                self._nlp_pipeline = pipeline("ner", model="dbmdz/bert-large-cased-finetuned-conll03-english")
            except Exception as e:
                print(f"Failed to load NLP pipeline: {e}")
                self.use_nlp = False
    
    def extract_entities(self, text: str) -> List[Entity]:
        """
        Extract entities from text using pattern matching and NLP.
        
        Args:
            text: Input text to extract entities from
            
        Returns:
            List of extracted entities
        """
        start_time = time.time()
        entities = []
        
        # Pattern-based extraction
        for entity_type, pattern in self.ENTITY_PATTERNS.items():
            if entity_type not in self.entity_types:
                continue
                
            for match in re.finditer(pattern, text):
                entity = Entity(
                    name=match.group(),
                    entity_type=entity_type,
                    confidence=0.8,
                    position=(match.start(), match.end()),
                    context=self._get_context(text, match.start(), match.end())
                )
                entities.append(entity)
        
        # NLP-based extraction if available
        if self.use_nlp and self._nlp_pipeline:
            try:
                nlp_entities = self._nlp_pipeline(text)
                
                # Group subwords
                current_entity = None
                for token in nlp_entities:
                    if token['entity'].startswith('B-'):
                        if current_entity:
                            entities.append(current_entity)
                        current_entity = Entity(
                            name=token['word'],
                            entity_type=token['entity'][2:],
                            confidence=token['score'],
                            position=(0, 0),  # Position not available in NLP output
                            context=""
                        )
                    elif token['entity'].startswith('I-') and current_entity:
                        current_entity.name += " " + token['word']
                
                if current_entity:
                    entities.append(current_entity)
                    
            except Exception as e:
                print(f"NLP extraction failed: {e}")
        
        # Remove duplicates and sort by confidence
        unique_entities = {}
        for entity in entities:
            key = (entity.name.lower(), entity.entity_type)
            if key not in unique_entities or entity.confidence > unique_entities[key].confidence:
                unique_entities[key] = entity
        
        # Sort by position in text
        sorted_entities = sorted(unique_entities.values(), key=lambda e: e.position[0])
        
        return sorted_entities
    
    def extract_relationships(self, text: str, entities: Optional[List[Entity]] = None) -> List[Relationship]:
        """
        Extract relationships between entities from text.
        
        Args:
            text: Input text to extract relationships from
            entities: Optional list of entities to constrain extraction
            
        Returns:
            List of extracted relationships
        """
        start_time = time.time()
        relationships = []
        
        # If entities provided, use them to constrain extraction
        if entities:
            entity_names = {e.name.lower() for e in entities}
        else:
            entity_names = set()
        
        # Pattern-based relationship extraction
        for pattern, rel_type in self.RELATIONSHIP_PATTERNS:
            for match in re.finditer(pattern, text, re.IGNORECASE):
                source = match.group(1)
                target = match.group(2)
                
                # If entity list provided, check if entities are in it
                if entity_names and (source.lower() not in entity_names and target.lower() not in entity_names):
                    continue
                
                relationship = Relationship(
                    source=source,
                    target=target,
                    relationship_type=rel_type,
                    confidence=0.7,
                    context=self._get_context(text, match.start(), match.end())
                )
                relationships.append(relationship)
        
        # Remove duplicates
        unique_relationships = {}
        for rel in relationships:
            key = (rel.source.lower(), rel.target.lower(), rel.relationship_type)
            if key not in unique_relationships or rel.confidence > unique_relationships[key].confidence:
                unique_relationships[key] = rel
        
        return list(unique_relationships.values())
    
    def extract_from_document(self, text: str) -> ExtractionResult:
        """
        Extract both entities and relationships from a document.
        
        Args:
            text: Document text
            
        Returns:
            ExtractionResult with entities and relationships
        """
        start_time = time.time()
        
        entities = self.extract_entities(text)
        relationships = self.extract_relationships(text, entities)
        
        return ExtractionResult(
            entities=entities,
            relationships=relationships,
            extraction_time_ms=(time.time() - start_time) * 1000
        )
    
    def _get_context(self, text: str, start: int, end: int, window: int = 50) -> str:
        """Get surrounding context for an entity."""
        context_start = max(0, start - window)
        context_end = min(len(text), end + window)
        return text[context_start:context_end].strip()
    
    def batch_extract(self, texts: List[str]) -> List[ExtractionResult]:
        """
        Extract entities and relationships from multiple texts.
        
        Args:
            texts: List of text documents
            
        Returns:
            List of ExtractionResult objects
        """
        return [self.extract_from_document(text) for text in texts]
