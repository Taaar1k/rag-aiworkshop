# Graph RAG Integration

This document describes the Graph RAG integration for the RAG system, which combines graph-based retrieval with vector search for enhanced information extraction.

## Overview

Graph RAG leverages graph databases to understand relationships between entities in documents. This approach is particularly effective for domains with complex relationships such as:

- **Legal**: Case law relationships, legal statutes, and precedents
- **Healthcare**: Patient conditions, treatments, and medications
- **Finance**: Transaction networks, company relationships, and financial flows

## Architecture

The Graph RAG system consists of three main components:

### 1. GraphRetriever

The core graph retrieval component that connects to Neo4j and performs graph traversals.

**Key Features:**
- Neo4j database connection management
- Entity extraction from queries
- Graph traversal with configurable depth
- Performance monitoring and caching

**Configuration:**
```python
from graph.graph_retriever import GraphRetrieverConfig

config = GraphRetrieverConfig(
    neo4j_uri="bolt://localhost:7687",
    neo4j_username="neo4j",
    neo4j_password="password",
    traversal_depth=2,
    max_results=10,
    use_caching=True
)
```

### 2. EntityExtractor

Extracts entities and relationships from text documents using pattern matching and NLP.

**Key Features:**
- Pattern-based entity extraction (PERSON, ORGANIZATION, LOCATION, DATE, etc.)
- Relationship extraction from text
- Batch processing support
- NLP integration (optional)

**Usage:**
```python
from graph.entity_extractor import EntityExtractor

extractor = EntityExtractor()
entities = extractor.extract_entities("Apple was founded by Steve Jobs in 1976.")
relationships = extractor.extract_relationships(text, entities)
```

### 3. HybridGraphRetriever

Combines graph and vector search for optimal retrieval results.

**Key Features:**
- Simultaneous graph and vector retrieval
- Weighted result fusion
- Optional reranking
- Performance monitoring

**Usage:**
```python
from graph.hybrid_graph_retriever import HybridGraphRetriever, HybridGraphRetrieverConfig

hybrid_config = HybridGraphRetrieverConfig(
    vector_weight=0.5,
    graph_weight=0.5,
    top_k=10
)

retriever = HybridGraphRetriever(
    graph_retriever=graph_retriever,
    vector_retriever=vector_retriever,
    config=hybrid_config
)

results = retriever.retrieve("query", top_k=10)
```

## Setup

### Neo4j Installation

1. **Install Neo4j** (choose one option):

   **Option A: Docker**
   ```bash
   docker run -d \
     -p 7474:7474 -p 7687:7687 \
     -e NEO4J_AUTH=neo4j/password \
     -e NEO4J_apoc_export_file_enabled=true \
     -e NEO4J_apoc_import_file_enabled=true \
     -e NEO4J_apoc_import_file_use_neo4j_config=true \
     neo4j:5.15
   ```

   **Option B: Manual Installation**
   Download from [neo4j.com](https://neo4j.com/download/) and follow installation instructions.

2. **Install Python dependencies:**
   ```bash
   pip install neo4j langchain-core
   ```

### Graph Schema Design

Design your graph schema based on your domain. Example for legal documents:

```cypher
// Entity nodes
CREATE (person:Entity {name: "John Doe", type: "PERSON"})
CREATE (company:Entity {name: "Acme Corp", type: "ORGANIZATION"})
CREATE (case:Entity {name: "Case v. Defendant", type: "CASE"})

// Relationship types
CREATE (person)-[:WORKS_AT]->(company)
CREATE (company)-[:INVOLVED_IN]->(case)
CREATE (case)-[:CITES]->(case)
```

## Usage Examples

### Basic Graph Retrieval

```python
from graph.graph_retriever import GraphRetriever, GraphRetrieverConfig

# Initialize
config = GraphRetrieverConfig(
    neo4j_uri="bolt://localhost:7687",
    traversal_depth=2
)
retriever = GraphRetriever(config=config)

# Retrieve with graph traversal
results = retriever.retrieve_with_graph("What is the relationship between Apple and Microsoft?")
```

### Entity Extraction

```python
from graph.entity_extractor import EntityExtractor

extractor = EntityExtractor()

# Extract entities
text = "Apple was founded by Steve Jobs in 1976."
entities = extractor.extract_entities(text)

# Extract relationships
relationships = extractor.extract_relationships(text, entities)
```

### Hybrid Retrieval

```python
from graph.hybrid_graph_retriever import HybridGraphRetriever, HybridGraphRetrieverConfig
from graph.graph_retriever import GraphRetriever, GraphRetrieverConfig

# Initialize components
graph_config = GraphRetrieverConfig(neo4j_uri="bolt://localhost:7687")
graph_retriever = GraphRetriever(config=graph_config)

# Assuming you have a vector retriever
hybrid_config = HybridGraphRetrieverConfig(
    vector_weight=0.5,
    graph_weight=0.5
)
hybrid_retriever = HybridGraphRetriever(
    graph_retriever=graph_retriever,
    vector_retriever=your_vector_retriever,
    config=hybrid_config
)

# Retrieve results
results = hybrid_retriever.retrieve("Your query", top_k=10)
```

## Performance Optimization

### Caching

Enable caching for common traversals:

```python
config = GraphRetrieverConfig(
    use_caching=True,
    cache_ttl_seconds=3600  # Cache for 1 hour
)
```

### Query Optimization

- Use appropriate traversal depth (start with 2, adjust based on results)
- Limit result counts
- Use relationship filters to narrow traversal

### Indexing in Neo4j

Create indexes for faster lookups:

```cypher
CREATE INDEX entity_name_index FOR (e:Entity) ON (e.name)
CREATE INDEX entity_type_index FOR (e:Entity) ON (e.type)
```

## Testing

Run the test suite:

```bash
# Unit tests
pytest ai_workspace/tests/test_graph_retriever.py -v
pytest ai_workspace/tests/test_entity_extractor.py -v

# Integration tests
pytest ai_workspace/tests/test_graph_integration.py -v

# All graph tests
pytest ai_workspace/tests/test_graph*.py -v
```

## API Reference

### GraphRetriever

| Method | Description |
|--------|-------------|
| `retrieve_with_graph(query, depth, max_results)` | Retrieve results using graph traversal |
| `find_relationships_between(entity1, entity2, max_depth)` | Find relationships between entities |
| `get_entity_info(entity_name)` | Get detailed information about an entity |
| `get_performance_stats()` | Get retrieval performance statistics |
| `clear_cache()` | Clear the traversal cache |

### EntityExtractor

| Method | Description |
|--------|-------------|
| `extract_entities(text)` | Extract entities from text |
| `extract_relationships(text, entities)` | Extract relationships from text |
| `extract_from_document(text)` | Extract both entities and relationships |
| `batch_extract(texts)` | Extract from multiple texts |

### HybridGraphRetriever

| Method | Description |
|--------|-------------|
| `retrieve(query, top_k, graph_depth)` | Retrieve using hybrid search |
| `set_weights(vector_weight, graph_weight)` | Update retrieval weights |
| `get_performance_stats()` | Get retrieval performance statistics |

## Troubleshooting

### Connection Issues

If Neo4j connection fails:
1. Verify Neo4j is running: `docker ps` (if using Docker)
2. Check credentials in config
3. Verify URI format: `bolt://host:port`

### Performance Issues

- Increase traversal depth gradually
- Use relationship filters
- Enable caching for repeated queries
- Consider adding Neo4j indexes

## Future Enhancements

- [ ] Support for additional graph databases (Amazon Neptune, Azure Cosmos DB)
- [ ] Advanced relationship extraction using NLP models
- [ ] Dynamic graph schema adaptation
- [ ] Graph-based query expansion
- [ ] Multi-hop reasoning across graph paths
