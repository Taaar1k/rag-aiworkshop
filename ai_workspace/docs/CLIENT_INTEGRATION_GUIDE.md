# Shared RAG Client Integration Guide

This guide explains how to integrate the Shared RAG system into your applications using the provided client SDKs.

## Overview

The Shared RAG system provides a unified API for RAG operations across multiple client applications. This guide covers:

- Python client SDK
- JavaScript/Node.js client SDK
- LM Studio plugin
- VS Code extension

## Prerequisites

- Running RAG server (default: `http://localhost:8000`)
- API key (if authentication is enabled)
- Python 3.8+ or Node.js 18+ for client SDKs

## Python Client SDK

### Installation

```bash
pip install requests
```

### Basic Usage

```python
from shared_rag.client import SharedRAGClient

# Initialize client
client = SharedRAGClient(
    base_url="http://localhost:8000",
    api_key="your_api_key"  # Optional
)

# Query the RAG system
result = client.query(
    query="What is quantum computing?",
    top_k=5,
    temperature=0.7
)

print(f"Answer: {result.answer}")
print(f"Sources: {result.sources}")
print(f"Query time: {result.query_time_ms:.2f}ms")

# Clean up
client.close()
```

### Advanced Usage

```python
# Upload a document
doc_info = client.upload_document(
    content="Your document content here",
    document_id="unique_id",
    metadata={"source": "file.txt", "category": "technical"}
)

# List documents
documents = client.list_documents(limit=100, offset=0)

# Generate embedding
embedding = client.generate_embedding("Text to embed")

# Health check
status = client.get_health_status()
```

### Error Handling

```python
from shared_rag.client import SharedRAGClient, AuthenticationError, APIError, ConnectionError

try:
    result = client.query("Your query")
except AuthenticationError:
    print("Authentication failed. Check your API key.")
except APIError as e:
    print(f"API Error {e.status_code}: {e.message}")
except ConnectionError:
    print("Connection failed. Is the server running?")
```

## JavaScript/Node.js Client SDK

### Installation

```bash
npm install axios
```

### Basic Usage

```javascript
import { SharedRAGJSClient } from './shared_rag/js_client.js';

// Initialize client
const client = new SharedRAGJSClient({
    baseURL: 'http://localhost:8000',
    apiKey: 'your_api_key', // Optional
    timeout: 30000,
    maxRetries: 3
});

// Query the RAG system
const result = await client.query('What is quantum computing?', {
    top_k: 5,
    temperature: 0.7
});

console.log(`Answer: ${result.answer}`);
console.log(`Sources: ${result.sources.length}`);
console.log(`Query time: ${result.query_time_ms}ms`);

// Clean up
client.close();
```

### Advanced Usage

```javascript
// Upload a document
const docInfo = await client.uploadDocument('Your document content', {
    documentId: 'unique_id',
    metadata: { source: 'file.txt', category: 'technical' }
});

// List documents
const documents = await client.listDocuments({ limit: 100, offset: 0 });

// Generate embedding
const embedding = await client.generateEmbedding('Text to embed');

// Health check
const status = await client.getHealthStatus();
```

### Error Handling

```javascript
import { AuthenticationError, APIError, ConnectionError } from './shared_rag/js_client.js';

try {
    const result = await client.query('Your query');
} catch (error) {
    if (error instanceof AuthenticationError) {
        console.error('Authentication failed. Check your API key.');
    } else if (error instanceof APIError) {
        console.error(`API Error ${error.statusCode}: ${error.message}`);
    } else if (error instanceof ConnectionError) {
        console.error('Connection failed. Is the server running?');
    }
}
```

## LM Studio Plugin

### Installation

1. Copy `lm_studio_plugin.py` to your LM Studio plugins directory
2. Configure the RAG API URL in the plugin settings

### Usage

```python
from shared_rag.lm_studio_plugin import create_lm_studio_plugin

# Create plugin
plugin = create_lm_studio_plugin(
    rag_api_url="http://localhost:8000",
    api_key="your_api_key"
)

# Query with context
result = plugin.query_with_context("Your query")

# Display sources
sources = plugin.get_sources("Your query", top_k=5)
formatted = plugin.display_sources(sources)
```

## VS Code Extension

### Installation

1. Open VS Code
2. Go to Extensions (Ctrl+Shift+X)
3. Search for "Shared RAG"
4. Click Install

### Usage

1. Open the Command Palette (Ctrl+Shift+P)
2. Type "Shared RAG" to see available commands:
   - `Shared RAG: Query` - Query the RAG system
   - `Shared RAG: Configure Connection` - Configure API URL and key
   - `Shared RAG: Show Sources` - Show sources for selected text
   - `Shared RAG: Upload Document` - Upload current document to RAG
   - `Shared RAG: Check Health` - Check server health

### Configuration

Add to your VS Code settings:

```json
{
    "sharedRAG.apiUrl": "http://localhost:8000",
    "sharedRAG.apiKey": "your_api_key",
    "sharedRAG.defaultTopK": 5,
    "sharedRAG.contextWindow": 4096
}
```

## API Reference

### Python Client

#### `SharedRAGClient`

```python
class SharedRAGClient:
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        verify_ssl: bool = True
    ):
        """Initialize the client."""
    
    def query(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict] = None,
        temperature: float = 0.7,
        max_tokens: int = 512
    ) -> QueryResult:
        """Query the RAG system."""
    
    def upload_document(
        self,
        content: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> DocumentInfo:
        """Upload a document to the vector store."""
    
    def delete_document(self, document_id: str) -> bool:
        """Delete a document from the vector store."""
    
    def list_documents(self, limit: int = 100, offset: int = 0) -> List[Dict]:
        """List documents in the vector store."""
    
    def get_health_status(self) -> Dict[str, Any]:
        """Get server health status."""
    
    def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for text."""
```

### JavaScript Client

#### `SharedRAGJSClient`

```javascript
class SharedRAGJSClient {
    constructor(options: {
        baseURL?: string;
        apiKey?: string;
        timeout?: number;
        maxRetries?: number;
    } = {});
    
    async query(query: string, options?: QueryOptions): Promise<QueryResult>;
    async uploadDocument(content: string, options?: UploadOptions): Promise<DocumentInfo>;
    async deleteDocument(documentId: string): Promise<boolean>;
    async listDocuments(options?: ListOptions): Promise<Array<Record<string, any>>>;
    async getHealthStatus(): Promise<Record<string, any>>;
    async generateEmbedding(text: string): Promise<Array<number>>;
    close(): void;
}
```

## Performance Considerations

- **Latency**: Target < 500ms for RAG queries
- **Connection Pooling**: Use session-based connections for Python client
- **Retry Logic**: Automatic retry with exponential backoff
- **Timeouts**: Default 30 seconds, configurable

## Security

- **Authentication**: API key via Bearer token
- **HTTPS**: Recommended for production
- **Rate Limiting**: Server-side rate limiting enabled
- **Data Isolation**: Tenant IDs in vector metadata

## Troubleshooting

### Connection Errors

- Verify server is running: `curl http://localhost:8000/health`
- Check firewall settings
- Verify API key is correct

### Authentication Errors

- Ensure API key is set correctly
- Check server authentication configuration
- Verify token format (Bearer token)

### Performance Issues

- Increase connection pool size
- Reduce `top_k` value
- Use caching for frequent queries
- Check server resource utilization

## Examples

See the following files for complete examples:

- Python: `ai_workspace/src/shared_rag/examples/python_example.py`
- JavaScript: `ai_workspace/src/shared_rag/examples/js_example.js`
- LM Studio: `ai_workspace/src/shared_rag/examples/lm_studio_example.py`

## Support

For issues and questions:

- Check the documentation
- Review the error messages
- Test with the benchmark and security audit scripts
