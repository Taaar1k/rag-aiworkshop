"""
Python Client SDK for Shared RAG System.

Provides programmatic access to the shared RAG system via REST API.
Supports authentication, error handling, and connection pooling.
"""

import os
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class SharedRAGError(Exception):
    """Base exception for Shared RAG client errors."""
    pass


class AuthenticationError(SharedRAGError):
    """Raised when authentication fails."""
    pass


class APIError(SharedRAGError):
    """Raised when API returns an error response."""
    def __init__(self, status_code: int, message: str, details: Optional[Dict] = None):
        self.status_code = status_code
        self.message = message
        self.details = details or {}
        super().__init__(f"API Error {status_code}: {message}")


class ConnectionError(SharedRAGError):
    """Raised when connection to the server fails."""
    pass


@dataclass
class QueryResult:
    """Result of a RAG query."""
    answer: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    query_time_ms: float = 0.0


@dataclass
class DocumentInfo:
    """Information about a document in the vector store."""
    id: str
    content: str
    metadata: Dict[str, Any]
    embedding_size: int = 0


class SharedRAGClient:
    """
    Python client for the Shared RAG system.
    
    Provides programmatic access to RAG operations including:
    - Querying with context
    - Document ingestion
    - Authentication management
    - Error handling and retry logic
    """
    
    def __init__(
        self,
        base_url: str = "http://localhost:8000",
        api_key: Optional[str] = None,
        timeout: float = 30.0,
        max_retries: int = 3,
        verify_ssl: bool = True
    ):
        """
        Initialize the Shared RAG client.
        
        Args:
            base_url: URL of the RAG server
            api_key: API key for authentication (can also be set via RAG_API_KEY env var)
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
            verify_ssl: Whether to verify SSL certificates
        """
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key or os.environ.get("RAG_API_KEY")
        self.timeout = timeout
        self.max_retries = max_retries
        self.verify_ssl = verify_ssl
        
        # Connection pooling with session
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "SharedRAG-Python-Client/1.0"
        })
        
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}"
            })
        
        logger.info(f"SharedRAGClient initialized: {self.base_url}")
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None,
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make an HTTP request with retry logic and error handling.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            endpoint: API endpoint path
            json_data: JSON payload for POST requests
            params: Query parameters
            
        Returns:
            JSON response as dictionary
            
        Raises:
            AuthenticationError: If authentication fails
            APIError: If API returns an error response
            ConnectionError: If connection fails
        """
        url = f"{self.base_url}{endpoint}"
        last_error = None
        
        for attempt in range(self.max_retries):
            try:
                response = self.session.request(
                    method=method,
                    url=url,
                    json=json_data,
                    params=params,
                    timeout=self.timeout,
                    verify=self.verify_ssl
                )
                
                # Handle authentication errors
                if response.status_code == 401:
                    raise AuthenticationError("Invalid or expired API key")
                
                # Handle other error responses
                if not response.ok:
                    error_details = {}
                    try:
                        error_details = response.json()
                    except ValueError:
                        error_details = {"raw": response.text}
                    
                    raise APIError(
                        status_code=response.status_code,
                        message=response.reason,
                        details=error_details
                    )
                
                return response.json()
                
            except requests.exceptions.Timeout:
                last_error = ConnectionError(f"Request timeout after {self.timeout}s")
                logger.warning(f"Request timeout (attempt {attempt + 1}/{self.max_retries})")
                
            except requests.exceptions.ConnectionError as e:
                last_error = ConnectionError(f"Connection failed: {str(e)}")
                logger.warning(f"Connection error (attempt {attempt + 1}/{self.max_retries})")
                
            except (AuthenticationError, APIError):
                # Don't retry authentication or API errors
                raise
                
            except Exception as e:
                last_error = SharedRAGError(f"Unexpected error: {str(e)}")
                logger.warning(f"Unexpected error (attempt {attempt + 1}/{self.max_retries})")
        
        # All retries failed
        raise last_error or SharedRAGError("All retry attempts failed")
    
    def query(
        self,
        query: str,
        top_k: int = 5,
        filters: Optional[Dict[str, Any]] = None,
        temperature: float = 0.7,
        max_tokens: int = 512
    ) -> QueryResult:
        """
        Query the shared RAG system.
        
        Args:
            query: The search query
            top_k: Number of relevant documents to retrieve
            filters: Optional filters for document search
            temperature: LLM temperature (0.0-1.0)
            max_tokens: Maximum tokens in response
            
        Returns:
            QueryResult with answer, sources, and metadata
        """
        start_time = datetime.now()
        
        request_data = {
            "model": "shared-rag-v1",
            "messages": [
                {"role": "user", "content": query}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
            "top_k": top_k,
            "filters": filters or {}
        }
        
        response = self._make_request(
            method="POST",
            endpoint="/v1/chat/completions",
            json_data=request_data
        )
        
        query_time = (datetime.now() - start_time).total_seconds() * 1000
        
        # Parse response
        choices = response.get("choices", [])
        if not choices:
            raise APIError(status_code=500, message="No choices in response")
        
        message = choices[0].get("message", {})
        answer = message.get("content", "")
        
        # Extract sources from metadata if available
        sources = []
        if "metadata" in response:
            sources = response["metadata"].get("sources", [])
        
        return QueryResult(
            answer=answer,
            sources=sources,
            metadata=response.get("metadata", {}),
            query_time_ms=query_time
        )
    
    def upload_document(
        self,
        content: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DocumentInfo:
        """
        Upload a document to the shared vector store.
        
        Args:
            content: Document content to embed and store
            document_id: Optional unique document identifier
            metadata: Optional metadata dictionary
            
        Returns:
            DocumentInfo with document details
        """
        request_data = {
            "content": content,
            "metadata": metadata or {}
        }
        
        if document_id:
            request_data["id"] = document_id
        
        response = self._make_request(
            method="POST",
            endpoint="/v1/documents",
            json_data=request_data
        )
        
        return DocumentInfo(
            id=response.get("id", ""),
            content=content,
            metadata=response.get("metadata", {}),
            embedding_size=response.get("embedding_size", 0)
        )
    
    def delete_document(self, document_id: str) -> bool:
        """
        Delete a document from the vector store.
        
        Args:
            document_id: ID of document to delete
            
        Returns:
            True if deletion was successful
        """
        self._make_request(
            method="DELETE",
            endpoint=f"/v1/documents/{document_id}"
        )
        return True
    
    def list_documents(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        """
        List documents in the vector store.
        
        Args:
            limit: Maximum number of documents to return
            offset: Offset for pagination
            
        Returns:
            List of document information dictionaries
        """
        response = self._make_request(
            method="GET",
            endpoint="/v1/documents",
            params={"limit": limit, "offset": offset}
        )
        
        return response.get("documents", [])
    
    def get_health_status(self) -> Dict[str, Any]:
        """
        Get server health status.
        
        Returns:
            Dictionary with server status information
        """
        return self._make_request(
            method="GET",
            endpoint="/health"
        )
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        Get server information.
        
        Returns:
            Dictionary with server configuration
        """
        return self._make_request(
            method="GET",
            endpoint="/info"
        )
    
    def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding for text.
        
        Args:
            text: Text to embed
            
        Returns:
            List of embedding values
        """
        response = self._make_request(
            method="POST",
            endpoint="/v1/embeddings",
            json_data={"input": text}
        )
        
        data = response.get("data", [])
        if not data:
            raise APIError(status_code=500, message="No embedding in response")
        
        return data[0].get("embedding", [])
    
    def close(self):
        """Close the session and clean up resources."""
        if self.session:
            self.session.close()
            logger.info("SharedRAGClient session closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False
    
    def __del__(self):
        """Destructor to ensure cleanup."""
        try:
            self.close()
        except Exception:
            pass


# Convenience function for quick queries
def quick_query(
    query: str,
    base_url: str = "http://localhost:8000",
    api_key: Optional[str] = None
) -> str:
    """
    Quick query function for simple use cases.
    
    Args:
        query: The search query
        base_url: URL of the RAG server
        api_key: API key for authentication
        
    Returns:
        Answer string from the RAG system
    """
    with SharedRAGClient(base_url=base_url, api_key=api_key) as client:
        result = client.query(query)
        return result.answer
