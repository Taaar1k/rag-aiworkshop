"""
Graph Retriever for Graph RAG System.

Implements graph-based retrieval using Neo4j for relationship-aware information extraction.
Supports entity extraction, graph traversal, and relationship-aware search.
"""

import os
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple
from collections import defaultdict

try:
    from neo4j import GraphDatabase, Driver, Session
    NEO4J_AVAILABLE = True
except ImportError:
    NEO4J_AVAILABLE = False
    print("Warning: neo4j package not installed. Install with: pip install neo4j")


@dataclass
class GraphRetrieverConfig:
    """Configuration for graph retriever."""
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_username: str = "neo4j"
    neo4j_password: str = os.getenv("NEO4J_PASSWORD", "")
    traversal_depth: int = 2
    max_results: int = 10
    relationship_filter: str = "RELATED_TO>"
    entity_label: str = "Entity"
    min_confidence: float = 0.5
    use_caching: bool = True
    cache_ttl_seconds: int = 3600


class GraphRetriever:
    """
    Graph-based retriever using Neo4j for relationship-aware search.
    
    Features:
    - Entity extraction from queries
    - Graph traversal with configurable depth
    - Relationship-aware retrieval
    - Performance monitoring and caching
    
    Args:
        config: Graph retriever configuration
        driver: Optional Neo4j driver instance
    """
    
    def __init__(
        self,
        config: Optional[GraphRetrieverConfig] = None,
        driver: Optional[Driver] = None
    ):
        self.config = config or GraphRetrieverConfig()
        self.driver = driver
        self._connected = False
        
        # Performance tracking
        self._latency_samples: List[float] = []
        self._max_latency_samples = 100
        
        # Cache for common traversals
        self._cache: Dict[str, Tuple[List[Dict], float]] = {}
        
        # Try to connect if credentials provided
        if not driver and self.config.neo4j_uri:
            self.connect()
    
    def connect(self) -> bool:
        """
        Establish connection to Neo4j database.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not NEO4J_AVAILABLE:
            print("Error: neo4j package not installed")
            return False
            
        if not self.config.neo4j_uri:
            print("Error: Neo4j URI not configured")
            return False
            
        # Fail loudly if Neo4j is enabled and password is missing
        if self.config.neo4j_uri and not self.config.neo4j_password:
            raise ValueError(
                "NEO4J_PASSWORD environment variable is required when Neo4j is enabled. "
                "Set it in your .env file or environment."
            )
            
        try:
            self.driver = GraphDatabase.driver(
                self.config.neo4j_uri,
                auth=(self.config.neo4j_username, self.config.neo4j_password)
            )
            # Test connection
            self.driver.verify_connectivity()
            self._connected = True
            return True
        except Exception as e:
            print(f"Failed to connect to Neo4j: {e}")
            self._connected = False
            return False
    
    def close(self) -> None:
        """Close Neo4j connection."""
        if self.driver:
            self.driver.close()
            self._connected = False
    
    def _extract_entities(self, query: str) -> List[Dict[str, Any]]:
        """
        Extract entities from query using pattern matching and heuristics.
        
        Args:
            query: Input query string
            
        Returns:
            List of extracted entities with metadata
        """
        entities = []
        
        # Pattern 1: Proper nouns (capitalized words)
        import re
        proper_nouns = re.findall(r'\b[A-Z][a-z]+(?: [A-Z][a-z]+)*\b', query)
        for pn in proper_nouns:
            if len(pn) > 1:  # Skip single letters
                entities.append({
                    "name": pn,
                    "type": "PROPER_NOUN",
                    "confidence": 0.7
                })
        
        # Pattern 2: Acronyms
        acronyms = re.findall(r'\b[A-Z]{2,}\b', query)
        for acronym in acronyms:
            entities.append({
                "name": acronym,
                "type": "ACRONYM",
                "confidence": 0.8
            })
        
        # Pattern 3: Numbers (dates, IDs, etc.)
        numbers = re.findall(r'\b\d{4}\b', query)  # Years
        for num in numbers:
            entities.append({
                "name": num,
                "type": "YEAR",
                "confidence": 0.6
            })
        
        # Filter by confidence threshold
        entities = [e for e in entities if e["confidence"] >= self.config.min_confidence]
        
        return entities[:5]  # Limit to top 5 entities
    
    def retrieve_with_graph(
        self,
        query: str,
        depth: Optional[int] = None,
        max_results: Optional[int] = None
    ) -> List[Dict]:
        """
        Retrieve context using graph traversal from extracted entities.
        
        Args:
            query: Search query string
            depth: Traversal depth (uses config default if None)
            max_results: Maximum results to return (uses config default if None)
            
        Returns:
            List of graph traversal results as dictionaries
        """
        start_time = time.time()
        
        depth = depth or self.config.traversal_depth
        max_results = max_results or self.config.max_results
        
        # Check cache first
        cache_key = f"{query}:{depth}:{max_results}"
        if self.config.use_caching and cache_key in self._cache:
            cached_result, _ = self._cache[cache_key]
            return cached_result
        
        # Extract entities from query
        entities = self._extract_entities(query)
        
        if not entities:
            return []
        
        # Build and execute graph traversal query
        results = []
        with self.driver.session() as session:
            for entity in entities:
                try:
                    # Cypher query for subgraph traversal
                    cypher = f"""
                    MATCH (e:{self.config.entity_label} {{name: $entity_name}})
                    CALL apoc.path.subgraphAll(e, {{
                        maxLevel: $depth,
                        relationshipFilter: $rel_filter
                    }})
                    YIELD nodes, relationships
                    RETURN nodes, relationships
                    """
                    
                    result = session.run(
                        cypher,
                        entity_name=entity["name"],
                        depth=depth,
                        rel_filter=self.config.relationship_filter
                    )
                    
                    # Process results
                    for record in result:
                        nodes = record.get("nodes", [])
                        relationships = record.get("relationships", [])
                        
                        # Convert to dictionary format
                        for node in nodes:
                            node_dict = {
                                "id": node.element_id,
                                "labels": list(node.labels),
                                "properties": dict(node.properties)
                            }
                            results.append({
                                "type": "node",
                                "data": node_dict,
                                "source_entity": entity["name"]
                            })
                        
                        for rel in relationships:
                            rel_dict = {
                                "id": rel.element_id,
                                "type": rel.type,
                                "start_node": rel.start_node.element_id,
                                "end_node": rel.end_node.element_id,
                                "properties": dict(rel.properties)
                            }
                            results.append({
                                "type": "relationship",
                                "data": rel_dict,
                                "source_entity": entity["name"]
                            })
                            
                except Exception as e:
                    # Continue with other entities if one fails
                    print(f"Error traversing entity {entity['name']}: {e}")
                    continue
        
        # Limit results
        results = results[:max_results]
        
        # Update cache
        if self.config.use_caching:
            self._cache[cache_key] = (results, time.time())
        
        # Track latency
        latency_ms = (time.time() - start_time) * 1000
        self._track_latency(latency_ms)
        
        return results
    
    def find_relationships_between(
        self,
        entity1: str,
        entity2: str,
        max_depth: int = 3
    ) -> List[Dict]:
        """
        Find all relationships between two entities within a depth.
        
        Args:
            entity1: First entity name
            entity2: Second entity name
            max_depth: Maximum path length to search
            
        Returns:
            List of relationship paths between entities
        """
        results = []
        
        with self.driver.session() as session:
            cypher = """
            MATCH path = (e1:Entity {name: $entity1})-[*1..$max_depth]-(e2:Entity {name: $entity2})
            WITH path, relationships(path) as rels, nodes(path) as nodes
            RETURN 
                [n in nodes | {label: head(labels(n)), name: n.name}] as path_nodes,
                [r in rels | {type: type(r), properties: properties(r)}] as path_rels,
                length(path) as path_length
            """
            
            try:
                result = session.run(
                    cypher,
                    entity1=entity1,
                    entity2=entity2,
                    max_depth=max_depth
                )
                
                for record in result:
                    results.append({
                        "path_nodes": record["path_nodes"],
                        "path_rels": record["path_rels"],
                        "path_length": record["path_length"]
                    })
            except Exception as e:
                print(f"Error finding relationships: {e}")
        
        return results
    
    def get_entity_info(self, entity_name: str) -> Dict:
        """
        Get detailed information about an entity.
        
        Args:
            entity_name: Name of the entity
            
        Returns:
            Entity information including labels, properties, and relationships
        """
        with self.driver.session() as session:
            cypher = """
            MATCH (e:Entity {name: $name})
            OPTIONAL MATCH (e)-[r]->(related)
            RETURN 
                e as entity,
                collect({
                    label: head(labels(e)),
                    properties: properties(e),
                    relationships: collect({
                        type: type(r),
                        target: head(labels(related)),
                        target_name: related.name
                    })
                }) as info
            """
            
            result = session.run(cypher, name=entity_name)
            record = result.single()
            
            if record:
                return {
                    "entity": dict(record["entity"].properties),
                    "relationships": record["info"]
                }
            return {}
    
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
            "p95_latency_ms": sorted(self._latency_samples)[int(len(self._latency_samples) * 0.95)] if len(self._latency_samples) > 1 else 0,
            "cache_size": len(self._cache)
        }
    
    def _get_doc_id(self, doc: Document) -> str:
        """Get unique document ID."""
        if hasattr(doc, 'metadata') and 'id' in doc.metadata:
            return str(doc.metadata['id'])
        if hasattr(doc, 'metadata') and 'doc_id' in doc.metadata:
            return str(doc.metadata['doc_id'])
        return str(hash(doc.page_content))
    
    def clear_cache(self) -> None:
        """Clear the traversal cache."""
        self._cache.clear()
    
    def __enter__(self):
        """Context manager entry."""
        if not self._connected:
            self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
