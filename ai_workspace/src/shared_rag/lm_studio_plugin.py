"""
LM Studio Plugin for Shared RAG System.

This module provides integration with LM Studio through the shared RAG API.
It enables LM Studio to use the shared RAG system for enhanced context and retrieval.
"""

import os
import requests
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class LMStudioPluginConfig:
    """Configuration for the LM Studio plugin."""
    rag_api_url: Optional[str] = None
    api_key: Optional[str] = None
    default_top_k: int = 5
    default_temperature: float = 0.7
    context_window_size: int = 4096


class LMStudioRAGPlugin:
    """
    LM Studio plugin for Shared RAG integration.
    
    Provides RAG capabilities to LM Studio by connecting to the shared RAG API.
    Features:
    - Query RAG system for context
    - Display sources in LM Studio interface
    - Manage RAG connections
    - Handle authentication
    """
    
    def __init__(self, config: Optional[LMStudioPluginConfig] = None):
        """
        Initialize the LM Studio RAG plugin.
        
        Args:
            config: Plugin configuration (uses defaults if None)
        """
        self.config = config or LMStudioPluginConfig()
        self.base_url = self.config.rag_api_url.rstrip("/")
        self.api_key = self.config.api_key or os.environ.get("RAG_API_KEY")
        
        # Setup session with connection pooling
        self.session = requests.Session()
        self.session.headers.update({
            "Content-Type": "application/json",
            "User-Agent": "LMStudio-RAG-Plugin/1.0"
        })
        
        if self.api_key:
            self.session.headers.update({
                "Authorization": f"Bearer {self.api_key}"
            })
        
        logger.info(f"LMStudioRAGPlugin initialized: {self.base_url}")
    
    def _make_request(
        self,
        method: str,
        endpoint: str,
        json_data: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Make HTTP request with error handling.
        
        Args:
            method: HTTP method
            endpoint: API endpoint
            json_data: Request body
            
        Returns:
            JSON response
            
        Raises:
            requests.exceptions.RequestException: On connection errors
        """
        url = f"{self.base_url}{endpoint}"
        
        try:
            response = self.session.request(
                method=method,
                url=url,
                json=json_data,
                timeout=30.0
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise
    
    def query_with_context(
        self,
        query: str,
        top_k: Optional[int] = None,
        filters: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Query the RAG system and get context for LM Studio.
        
        Args:
            query: The search query
            top_k: Number of documents to retrieve (uses config default if None)
            filters: Optional filters for document search
            
        Returns:
            Dictionary with answer and sources
        """
        top_k = top_k or self.config.default_top_k
        
        request_data = {
            "model": "shared-rag-v1",
            "messages": [
                {"role": "user", "content": query}
            ],
            "temperature": self.config.default_temperature,
            "top_k": top_k,
            "filters": filters or {}
        }
        
        response = self._make_request(
            method="POST",
            endpoint="/v1/chat/completions",
            json_data=request_data
        )
        
        return response
    
    def get_sources(self, query: str, top_k: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get source documents for a query.
        
        Args:
            query: The search query
            top_k: Number of sources to retrieve
            
        Returns:
            List of source documents with metadata
        """
        result = self.query_with_context(query, top_k)
        return result.get("metadata", {}).get("sources", [])
    
    def display_sources(self, sources: List[Dict[str, Any]]) -> str:
        """
        Format sources for display in LM Studio.
        
        Args:
            sources: List of source documents
            
        Returns:
            Formatted string for LM Studio interface
        """
        if not sources:
            return "No sources found."
        
        formatted = []
        for i, source in enumerate(sources, 1):
            content = source.get("content", "")
            score = source.get("score", 0)
            metadata = source.get("metadata", {})
            
            # Truncate content if too long
            display_content = content[:200] + "..." if len(content) > 200 else content
            
            formatted.append(
                f"[{i}] Score: {score:.4f}\n"
                f"Content: {display_content}\n"
                f"Metadata: {metadata}"
            )
        
        return "\n\n".join(formatted)
    
    def connect(self) -> bool:
        """
        Test connection to the RAG API.
        
        Returns:
            True if connection successful
        """
        try:
            response = self.session.get(
                f"{self.base_url}/health",
                timeout=5.0
            )
            return response.status_code == 200
        except requests.exceptions.RequestException:
            return False
    
    def get_server_info(self) -> Dict[str, Any]:
        """
        Get server information.
        
        Returns:
            Server configuration information
        """
        return self._make_request(
            method="GET",
            endpoint="/info"
        )
    
    def upload_document(
        self,
        content: str,
        document_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Upload a document to the RAG system.
        
        Args:
            content: Document content
            document_id: Optional unique document ID
            metadata: Optional metadata
            
        Returns:
            Upload result with document info
        """
        request_data = {
            "content": content,
            "metadata": metadata or {}
        }
        
        if document_id:
            request_data["id"] = document_id
        
        return self._make_request(
            method="POST",
            endpoint="/v1/documents",
            json_data=request_data
        )
    
    def close(self):
        """Close the session and clean up resources."""
        if self.session:
            self.session.close()
            logger.info("LMStudioRAGPlugin session closed")
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
        return False


def create_lm_studio_plugin(
    rag_api_url: Optional[str] = None,
    api_key: Optional[str] = None
) -> LMStudioRAGPlugin:
    """
    Factory function to create an LM Studio RAG plugin.
    
    Args:
        rag_api_url: URL of the RAG API server
        api_key: API key for authentication
        
    Returns:
        Configured LMStudioRAGPlugin instance
    """
    actual_url = rag_api_url or os.getenv("RAG_SERVER_URL", "http://localhost:8000")
    config = LMStudioPluginConfig(
        rag_api_url=actual_url,
        api_key=api_key
    )
    return LMStudioRAGPlugin(config=config)
