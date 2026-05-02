"""
Hybrid Retriever for RAG System.
Combines vector and keyword search via Reciprocal Rank Fusion.
"""

from dataclasses import dataclass
from typing import Any, Dict, List, Optional

from langchain_core.documents import Document


@dataclass
class HybridRetrieverConfig:
    """Configuration for hybrid retriever."""
    vector_weight: float = 0.3
    keyword_weight: float = 0.7
    rrf_k: float = 60
    top_k: int = 10
    deduplicate: bool = True


class HybridRetriever:
    """Hybrid retriever combining vector and keyword search via RRF."""

    def __init__(
        self,
        vector_retriever: Any,
        keyword_retriever: Any,
        config: Optional[HybridRetrieverConfig] = None
    ):
        self.vector_retriever = vector_retriever
        self.keyword_retriever = keyword_retriever
        self.config = config or HybridRetrieverConfig()

    def _get_doc_id(self, doc: Document) -> str:
        """Get unique document ID."""
        if hasattr(doc, 'metadata'):
            for key in ('item_id', 'doc_id', 'id'):
                if key in doc.metadata:
                    return doc.metadata[key]
        return hash(doc.page_content)

    def _fuse_results(
        self,
        vector_docs: List[Document],
        keyword_docs: List[Document]
    ) -> List[Document]:
        """Apply RRF and combine results."""
        doc_scores: Dict[str, float] = {}
        doc_data: Dict[str, Document] = {}

        # Vector contribution
        for rank, doc in enumerate(vector_docs, 1):
            doc_id = self._get_doc_id(doc)
            if doc_id not in doc_data:
                doc_data[doc_id] = doc
            score = 1.0 / (rank + self.config.rrf_k)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + self.config.vector_weight * score

        # Keyword contribution
        for rank, doc in enumerate(keyword_docs, 1):
            doc_id = self._get_doc_id(doc)
            if doc_id not in doc_data:
                doc_data[doc_id] = doc
            score = 1.0 / (rank + self.config.rrf_k)
            doc_scores[doc_id] = doc_scores.get(doc_id, 0) + self.config.keyword_weight * score

        # Sort by score
        sorted_ids = sorted(doc_scores.keys(), key=lambda x: doc_scores[x], reverse=True)

        results = []
        for doc_id in sorted_ids:
            doc = doc_data[doc_id]
            if not hasattr(doc, 'metadata'):
                doc.metadata = {}
            doc.metadata['hybrid_score'] = doc_scores[doc_id]
            results.append(doc)

        return results

    def retrieve(
        self,
        query: str,
        top_k: Optional[int] = None,
        vector_k: int = 10,
        keyword_k: int = 10,
    ) -> List[Document]:
        """Execute hybrid search."""
        top_k = top_k or self.config.top_k

        vector_docs = self.vector_retriever.invoke(query, k=vector_k) if self.vector_retriever else []
        keyword_docs = self.keyword_retriever.invoke(query, k=keyword_k) if self.keyword_retriever else []

        results = self._fuse_results(vector_docs, keyword_docs)

        if self.config.deduplicate:
            seen = set()
            deduped = []
            for doc in results:
                doc_id = self._get_doc_id(doc)
                if doc_id not in seen:
                    seen.add(doc_id)
                    deduped.append(doc)
            results = deduped

        return results[:top_k]

    def get_config(self) -> Dict[str, Any]:
        """Get current configuration."""
        return {
            "vector_weight": self.config.vector_weight,
            "keyword_weight": self.config.keyword_weight,
            "rrf_k": self.config.rrf_k,
            "top_k": self.config.top_k,
            "deduplicate": self.config.deduplicate,
        }
