"""
Tests for Multi-Modal Support: Unified Retriever
"""

import unittest
import torch
from pathlib import Path
from PIL import Image
import numpy as np

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from src.multimodal.image_encoder import ImageEncoder
from src.multimodal.unified_retriever import UnifiedRetriever, RetrievalResult, ModalityType


class MockVectorStore:
    """Mock vector store for testing."""

    def __init__(self):
        self.collections = {
            "text_documents": [],
            "image_embeddings": []
        }

    def search(
        self,
        query_embedding: torch.Tensor,
        collection: str,
        top_k: int = 10
    ) -> list[dict]:
        """Mock search implementation."""
        # Return mock results
        return [
            {
                "id": f"doc_{i}",
                "score": float(0.9 - i * 0.05),
                "content": f"Mock content {i}",
                "metadata": {"source": "test"}
            }
            for i in range(min(top_k, 5))
        ]


class TestUnifiedRetriever(unittest.TestCase):
    """Test cases for UnifiedRetriever."""

    def setUp(self):
        """Set up test fixtures."""
        self.encoder = ImageEncoder(
            model_name="openai/clip-vit-base-patch32",
            device="cpu"
        )

        self.vector_store = MockVectorStore()
        self.retriever = UnifiedRetriever(
            vector_store=self.vector_store,
            image_encoder=self.encoder
        )

        # Create a test image
        self.test_image_path = "test_image.jpg"
        test_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        test_image = Image.fromarray(test_array, mode="RGB")
        test_image.save(self.test_image_path)

    def tearDown(self):
        """Clean up test fixtures."""
        if Path(self.test_image_path).exists():
            Path(self.test_image_path).unlink()

    def test_retriever_initialization(self):
        """Test retriever initialization."""
        self.assertIsNotNone(self.retriever.vector_store)
        self.assertIsNotNone(self.retriever.image_encoder)
        self.assertEqual(
            self.retriever.text_collection_name,
            "text_documents"
        )

    def test_retrieve_by_text(self):
        """Test text-based retrieval."""
        query = "test query"
        results = self.retriever.retrieve_by_text(
            query_text=query,
            modalities=[ModalityType.TEXT, ModalityType.IMAGE],
            top_k=5
        )

        # Check results
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

        # Check result types
        for result in results:
            self.assertIsInstance(result, RetrievalResult)
            self.assertIn(result.type, ["text", "image"])

    def test_retrieve_by_image(self):
        """Test image-based retrieval."""
        results = self.retriever.retrieve_by_image(
            image_path=self.test_image_path,
            modalities=[ModalityType.TEXT, ModalityType.IMAGE],
            top_k=5
        )

        # Check results
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)

    def test_retrieve_with_single_modality(self):
        """Test retrieval with single modality."""
        query = "test query"

        # Text only
        text_results = self.retriever.retrieve(
            query=query,
            modalities=[ModalityType.TEXT],
            top_k=5,
            query_type="text"
        )

        self.assertEqual(len(text_results), 5)
        self.assertTrue(all(r.type == "text" for r in text_results))

        # Image only
        image_results = self.retriever.retrieve(
            query=query,
            modalities=[ModalityType.IMAGE],
            top_k=5,
            query_type="text"
        )

        self.assertEqual(len(image_results), 5)
        self.assertTrue(all(r.type == "image" for r in image_results))

    def test_retrieval_result_to_dict(self):
        """Test RetrievalResult serialization."""
        result = RetrievalResult(
            id="test_id",
            type="text",
            score=0.95,
            content="Test content",
            metadata={"key": "value"}
        )

        result_dict = result.to_dict()

        self.assertEqual(result_dict["id"], "test_id")
        self.assertEqual(result_dict["type"], "text")
        self.assertEqual(result_dict["score"], 0.95)
        self.assertEqual(result_dict["content"], "Test content")
        self.assertEqual(result_dict["metadata"]["key"], "value")


if __name__ == "__main__":
    unittest.main()
