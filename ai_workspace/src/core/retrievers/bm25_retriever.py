"""
BM25 Keyword Retriever for RAG System.

Implements BM25 (Best Matching Keyword 25) algorithm for keyword-based search.
Provides fast, exact-match retrieval complementing vector semantic search.
"""

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Union
from pathlib import Path

from rank_bm25 import BM25Okapi
from langchain_core.documents import Document


@dataclass
class BM25Config:
    """Configuration for BM25 retriever."""
    persist_directory: str = "./ai_workspace/memory/bm25_index"
    k1: float = 1.5  # Term frequency saturation
    b: float = 0.75  # Length normalization
    language: str = "en"  # Tokenizer language
    min_token_length: int = 2  # Minimum token length
    max_tokens: int = 10000  # Maximum tokens per document


class BM25Retriever:
    """
    BM25-based keyword retriever for exact-match search.
    
    Features:
    - BM25Okapi algorithm implementation
    - Persistent index storage
    - Configurable tokenization
    - Fast keyword-based retrieval
    
    Args:
        config: BM25 configuration
        documents: Initial documents to index (optional)
    """
    
    def __init__(
        self,
        config: Optional[BM25Config] = None,
        documents: Optional[List[Document]] = None
    ):
        self.config = config or BM25Config()
        self._bm25_index: Optional[BM25Okapi] = None
        self._document_store: List[Dict[str, Any]] = []
        self._index_path = Path(self.config.persist_directory)
        
        # Tokenizer for BM25
        self._tokenizer = self._get_tokenizer()
        
        # Index documents if provided
        if documents:
            self.index_documents(documents)
    
    def _get_tokenizer(self):
        """Get language-specific tokenizer."""
        def tokenize(text: str) -> List[str]:
            """Simple tokenization with language support."""
            # Lowercase
            text = text.lower()
            
            # Language-specific handling
            if self.config.language == "uk":
                # Ukrainian: preserve Cyrillic characters
                tokens = re.findall(r'\b[a-zа-яієґ]+\b', text)
            elif self.config.language == "ru":
                # Russian: preserve Cyrillic characters
                tokens = re.findall(r'\b[a-zа-яё]+\b', text)
            else:
                # English/default: ASCII letters
                tokens = re.findall(r'\b[a-z]+\b', text)
            
            # Filter short tokens
            tokens = [t for t in tokens if len(t) >= self.config.min_token_length]
            
            # Limit tokens
            tokens = tokens[:self.config.max_tokens]
            
            return tokens
        
        return tokenize
    
    def _tokenize_document(self, text: str) -> List[str]:
        """Tokenize document text for BM25 indexing."""
        return self._tokenizer(text)
    
    def index_documents(self, documents: Union[Document, Dict[str, Any], List[Document]]) -> int:
        """
        Index documents into BM25 retriever.
        
        Args:
            documents: Document, dict, or list of documents to index
            
        Returns:
            Number of documents indexed
        """
        # Normalize input
        if isinstance(documents, dict):
            docs = [Document(page_content=str(documents.get("content", "")), metadata=documents)]
        elif isinstance(documents, Document):
            docs = [documents]
        else:
            docs = documents
        
        # Tokenize and store
        tokenized_docs = []
        for doc in docs:
            if isinstance(doc, dict):
                content = str(doc.get("content", ""))
                metadata = doc
            else:
                content = doc.page_content
                metadata = doc.metadata if hasattr(doc, 'metadata') else {}
            
            tokens = self._tokenize_document(content)
            if tokens:  # Only index non-empty documents
                tokenized_docs.append(tokens)
                self._document_store.append({
                    "content": content,
                    "metadata": metadata,
                    "tokens": tokens
                })
        
        # Rebuild index if this is first batch
        if self._bm25_index is None:
            self._bm25_index = BM25Okapi(tokenized_docs)
        else:
            # Append to existing index
            self._bm25_index._doc_scores = None  # Reset cached scores
            self._bm25_index._tokenized_docs = self._bm25_index._tokenized_docs + tokenized_docs
            # Recalculate statistics
            from rank_bm25 import _calculate_idf
            self._bm25_index._calculate_tf()
        
        return len(tokenized_docs)
    
    def load_index(self) -> bool:
        """
        Load BM25 index from persistent storage.
        
        Returns:
            True if index loaded successfully, False otherwise
        """
        try:
            index_path = self._index_path / "bm25_index.json"
            if not index_path.exists():
                return False
            
            import json
            with open(index_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Reconstruct index
            tokenized_docs = data.get("tokenized_docs", [])
            self._bm25_index = BM25Okapi(tokenized_docs)
            self._document_store = data.get("document_store", [])
            
            return True
        except Exception as e:
            print(f"Error loading BM25 index: {e}")
            return False
    
    def save_index(self) -> bool:
        """
        Save BM25 index to persistent storage.
        
        Returns:
            True if saved successfully, False otherwise
        """
        try:
            self._index_path.mkdir(parents=True, exist_ok=True)
            
            import json
            data = {
                "tokenized_docs": [doc["tokens"] for doc in self._document_store],
                "document_store": self._document_store,
                "config": {
                    "k1": self.config.k1,
                    "b": self.config.b,
                    "language": self.config.language
                }
            }
            
            index_path = self._index_path / "bm25_index.json"
            with open(index_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            
            return True
        except Exception as e:
            print(f"Error saving BM25 index: {e}")
            return False
    
    def search(
        self,
        query: str,
        k: int = 5,
        min_score: float = 0.0
    ) -> List[Document]:
        """
        Search documents using BM25 algorithm.
        
        Args:
            query: Search query string
            k: Number of top results to return
            min_score: Minimum BM25 score threshold
            
        Returns:
            List of relevant documents sorted by BM25 score
        """
        if self._bm25_index is None or len(self._document_store) == 0:
            return []
        
        # Tokenize query
        query_tokens = self._tokenize_document(query)
        if not query_tokens:
            return []
        
        # Get BM25 scores
        scores = self._bm25_index.get_scores(query_tokens)
        
        # Create ranked results with scores
        results = []
        for idx, score in enumerate(scores):
            doc_data = self._document_store[idx]
            doc = Document(
                page_content=doc_data["content"],
                metadata={
                    **doc_data["metadata"],
                    "bm25_score": float(score),
                    "retrieval_type": "keyword"
                }
            )
            results.append((idx, doc, score))
        
        # Sort by score (descending)
        results.sort(key=lambda x: x[2], reverse=True)
        
        # Return top-k as Document objects
        # Filter by min_score after sorting
        filtered_results = [doc for _, doc, score in results if score >= min_score]
        return filtered_results[:k]
    
    def invoke(self, query: str, k: int = 5, min_score: float = 0.0) -> List[Document]:
        """
        Invoke BM25 search (LangChain-compatible interface).
        
        Args:
            query: Search query string
            k: Number of results to return
            min_score: Minimum score threshold
            
        Returns:
            List of relevant documents
        """
        return self.search(query, k, min_score)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get BM25 retriever statistics."""
        doc_count = len(self._document_store)
        total_tokens = sum(len(doc["tokens"]) for doc in self._document_store)
        
        return {
            "document_count": doc_count,
            "total_tokens": total_tokens,
            "avg_tokens_per_doc": total_tokens / doc_count if doc_count > 0 else 0,
            "k1": self.config.k1,
            "b": self.config.b,
            "language": self.config.language,
            "index_path": str(self._index_path)
        }
    
    def clear_index(self) -> None:
        """Clear all indexed documents."""
        self._bm25_index = None
        self._document_store = []
