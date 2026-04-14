"""
Shared RAG Client SDK Package
Provides clients for LM Studio, VS Code, and programmatic access to the shared RAG system.
"""

from .client import SharedRAGClient
from .js_client import SharedRAGJSClient

__all__ = ["SharedRAGClient", "SharedRAGJSClient"]
