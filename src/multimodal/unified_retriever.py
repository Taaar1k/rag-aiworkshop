"""
Multi-Modal Support: Unified Retriever for Cross-Modal Search
"""

from typing import List, Dict, Optional, Union
import torch
from dataclasses import dataclass
from enum import Enum

from .image_encoder import ImageEncoder


class ModalityType(str, Enum):
    """Supported modalities for retrieval."""
    TEXT = "text"
    IMAGE = "image"


@dataclass
class RetrievalResult:
    """Result from unified retrieval."""
    id: str
    type: str  # 'text' or 'image'
    score: float
    content: Union[str, Dict]
    metadata: Dict

    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type,
            "score": float(self.score),
            "content": self.content,
            "metadata": self.metadata
        }


class UnifiedRetriever:
    """
    Unified retriever for cross-modal search across text and images.
    Uses CLIP embedding space for unified representation.
    """

    def __init__(
        self,
        vector_store,
        image_encoder: ImageEncoder,
        text_collection_name: str = "text_documents",
        image_collection_name: str = "image_embeddings"
    ):
        """
        Initialize unified retriever.

        Args:
            vector_store: Vector store instance with collections
            image_encoder: ImageEncoder instance for CLIP embeddings
            text_collection_name: Name of text documents collection
            image_collection_name: Name of image embeddings collection
        """
        self.vector_store = vector_store
        self.image_encoder = image_encoder
        self.text_collection_name = text_collection_name
        self.image_collection_name = image_collection_name

    def retrieve(
        self,
        query: Union[str, torch.Tensor],
        modalities: List[ModalityType] = [ModalityType.TEXT, ModalityType.IMAGE],
        top_k: int = 10,
        query_type: str = "text"
    ) -> List[RetrievalResult]:
        """
        Retrieve from unified space across modalities.

        Args:
            query: Query string or pre-computed embedding
            modalities: List of modalities to search (text, image, or both)
            top_k: Maximum number of results to return per modality
            query_type: Type of query ('text' or 'image')

        Returns:
            List[RetrievalResult]: Ranked results from all modalities
        """
        results = []

        # Encode query
        if isinstance(query, str):
            if query_type == "text":
                query_embedding = self.image_encoder.encode_text(query)
            else:
                # Assume query is image path
                query_embedding = self.image_encoder.encode_image(query)
        else:
            query_embedding = query

        # Search text documents
        if ModalityType.TEXT in modalities:
            text_results = self._search_text(query_embedding, top_k)
            results.extend(text_results)

        # Search images
        if ModalityType.IMAGE in modalities:
            image_results = self._search_images(query_embedding, top_k)
            results.extend(image_results)

        # Re-rank unified results
        return self._rerank_unified(results, query)

    def _search_text(
        self,
        query_embedding: torch.Tensor,
        top_k: int
    ) -> List[RetrievalResult]:
        """Search text documents collection."""
        results = self.vector_store.search(
            query_embedding,
            collection=self.text_collection_name,
            top_k=top_k
        )

        return [
            RetrievalResult(
                id=result["id"],
                type="text",
                score=result["score"],
                content=result["content"],
                metadata=result.get("metadata", {})
            )
            for result in results
        ]

    def _search_images(
        self,
        query_embedding: torch.Tensor,
        top_k: int
    ) -> List[RetrievalResult]:
        """Search image embeddings collection."""
        results = self.vector_store.search(
            query_embedding,
            collection=self.image_collection_name,
            top_k=top_k
        )

        return [
            RetrievalResult(
                id=result["id"],
                type="image",
                score=result["score"],
                content=result["content"],
                metadata=result.get("metadata", {})
            )
            for result in results
        ]

    def _rerank_unified(
        self,
        results: List[RetrievalResult],
        query: Union[str, torch.Tensor]
    ) -> List[RetrievalResult]:
        """
        Re-rank results from multiple modalities using cross-encoder.

        Args:
            results: Unranked results from all modalities
            query: Original query

        Returns:
            List[RetrievalResult]: Re-ranked results
        """
        # Sort by initial score
        sorted_results = sorted(results, key=lambda x: x.score, reverse=True)

        # Return top_k results
        return sorted_results[:10]

    def retrieve_by_image(
        self,
        image_path: str,
        modalities: List[ModalityType] = [ModalityType.TEXT, ModalityType.IMAGE],
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """
        Retrieve similar text and images given an image query.

        Args:
            image_path: Path to query image
            modalities: Modalities to search
            top_k: Results per modality

        Returns:
            List[RetrievalResult]: Ranked results
        """
        return self.retrieve(
            query=image_path,
            modalities=modalities,
            top_k=top_k,
            query_type="image"
        )

    def retrieve_by_text(
        self,
        query_text: str,
        modalities: List[ModalityType] = [ModalityType.TEXT, ModalityType.IMAGE],
        top_k: int = 10
    ) -> List[RetrievalResult]:
        """
        Retrieve similar text and images given a text query.

        Args:
            query_text: Text query
            modalities: Modalities to search
            top_k: Results per modality

        Returns:
            List[RetrievalResult]: Ranked results
        """
        return self.retrieve(
            query=query_text,
            modalities=modalities,
            top_k=top_k,
            query_type="text"
        )
