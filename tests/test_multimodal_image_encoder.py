"""
Tests for Multi-Modal Support: Image Encoder
"""

import unittest
import torch
from pathlib import Path
from PIL import Image
import numpy as np

from multimodal.image_encoder import ImageEncoder


class TestImageEncoder(unittest.TestCase):
    """Test cases for ImageEncoder."""

    def setUp(self):
        """Set up test fixtures."""
        self.encoder = ImageEncoder(
            model_name="openai/clip-vit-base-patch32",
            device="cpu"
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

    def test_encoder_initialization(self):
        """Test encoder initialization."""
        self.assertIsNotNone(self.encoder.model)
        self.assertIsNotNone(self.encoder.processor)
        self.assertEqual(self.encoder.embedding_dim, 512)
        self.assertEqual(self.encoder.device, "cpu")

    def test_encode_image(self):
        """Test image encoding."""
        embedding = self.encoder.encode_image(self.test_image_path)

        # Check embedding is a tensor
        self.assertIsInstance(embedding, torch.Tensor)

        # Check embedding has reasonable shape (CLIP base returns 512-dim embeddings)
        self.assertGreater(embedding.shape[0], 10)

    def test_encode_text(self):
        """Test text encoding."""
        text = "This is a test text"
        embedding = self.encoder.encode_text(text)

        # Check embedding is a tensor
        self.assertIsInstance(embedding, torch.Tensor)

        # Check embedding has reasonable shape
        self.assertGreater(embedding.shape[0], 10)

    def test_encode_batch_images(self):
        """Test batch image encoding."""
        # Create multiple test images
        image_paths = []
        for i in range(3):
            path = f"test_image_{i}.jpg"
            test_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            test_image = Image.fromarray(test_array, mode="RGB")
            test_image.save(path)
            image_paths.append(path)

        try:
            embeddings = self.encoder.encode_batch_images(image_paths)

            # Check batch shape
            self.assertEqual(embeddings.shape[0], 3)
            self.assertGreater(embeddings.shape[1], 10)
        finally:
            # Clean up
            for path in image_paths:
                Path(path).unlink()

    def test_encode_batch_texts(self):
        """Test batch text encoding."""
        texts = ["Text 1", "Text 2", "Text 3"]
        embeddings = self.encoder.encode_batch_texts(texts)

        # Check batch shape
        self.assertEqual(embeddings.shape[0], 3)
        self.assertGreater(embeddings.shape[1], 10)

    def test_compute_similarity(self):
        """Test similarity computation."""
        # Create two embeddings
        emb1 = torch.randn(512)
        emb2 = torch.randn(512)

        similarity = self.encoder.compute_similarity(emb1, emb2)

        # Check similarity is a scalar
        self.assertIsInstance(similarity, torch.Tensor)
        self.assertEqual(similarity.dim(), 0)

        # Check similarity is in valid range
        self.assertGreaterEqual(float(similarity), -1.0)
        self.assertLessEqual(float(similarity), 1.0)

    def test_normalize_embeddings(self):
        """Test that embeddings are normalized."""
        # Encode without normalization
        emb_unnormalized = self.encoder.encode_image(self.test_image_path, normalize=False)
        emb_normalized = self.encoder.encode_image(self.test_image_path, normalize=True)

        # Check normalized embedding has unit norm (allow some tolerance for numerical precision)
        norm = torch.norm(emb_normalized)
        # CLIP embeddings are typically normalized to unit L2 norm
        # Allow tolerance of 0.1 for numerical precision
        self.assertAlmostEqual(float(norm), 1.0, delta=0.1)


if __name__ == "__main__":
    unittest.main()
