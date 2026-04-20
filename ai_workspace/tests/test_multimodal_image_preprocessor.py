"""
Tests for Multi-Modal Support: Image Preprocessor
"""

import unittest
import torch
from pathlib import Path
from PIL import Image
import numpy as np

from multimodal.image_preprocessor import ImagePreprocessor, ImageCaptionExtractor


class TestImagePreprocessor(unittest.TestCase):
    """Test cases for ImagePreprocessor."""

    def setUp(self):
        """Set up test fixtures."""
        self.preprocessor = ImagePreprocessor(
            target_size=(224, 224),
            normalize=True
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

    def test_preprocessor_initialization(self):
        """Test preprocessor initialization."""
        self.assertEqual(self.preprocessor.target_size, (224, 224))
        self.assertTrue(self.preprocessor.normalize)

    def test_preprocess(self):
        """Test image preprocessing."""
        result = self.preprocessor.preprocess(self.test_image_path)

        # Check result structure
        self.assertIn("image", result)
        self.assertIn("tensor", result)
        self.assertIn("array", result)
        self.assertIn("original_size", result)
        self.assertIn("processed_size", result)

        # Check tensor shape (CHW format)
        self.assertEqual(result["tensor"].shape[0], 3)  # RGB channels

    def test_preprocess_batch(self):
        """Test batch preprocessing."""
        # Create multiple test images
        image_paths = []
        for i in range(3):
            path = f"test_image_{i}.jpg"
            test_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            test_image = Image.fromarray(test_array, mode="RGB")
            test_image.save(path)
            image_paths.append(path)

        try:
            results = self.preprocessor.preprocess_batch(image_paths)

            # Check batch results
            self.assertEqual(len(results), 3)
            self.assertTrue(all("tensor" in r for r in results))
        finally:
            # Clean up
            for path in image_paths:
                Path(path).unlink()

    def test_normalize_array(self):
        """Test array normalization."""
        # Create test array
        test_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)

        # Normalize
        normalized = self.preprocessor._normalize_array(test_array)

        # Check normalization
        self.assertLess(normalized.max(), 10)  # Should be normalized
        self.assertGreater(normalized.min(), -10)

    def test_array_to_tensor(self):
        """Test array to tensor conversion."""
        test_array = np.random.rand(100, 100, 3).astype(np.float32)

        tensor = self.preprocessor._array_to_tensor(test_array)

        # Check tensor shape (CHW format)
        self.assertEqual(tensor.shape[0], 3)  # RGB channels
        self.assertIsInstance(tensor, torch.Tensor)

    def test_extract_metadata(self):
        """Test metadata extraction."""
        metadata = self.preprocessor.extract_metadata(self.test_image_path)

        # Check metadata fields
        self.assertIn("path", metadata)
        self.assertIn("format", metadata)
        self.assertIn("size", metadata)
        self.assertIn("width", metadata)
        self.assertIn("height", metadata)
        self.assertIn("file_size", metadata)


class TestImageCaptionExtractor(unittest.TestCase):
    """Test cases for ImageCaptionExtractor."""

    def setUp(self):
        """Set up test fixtures."""
        self.caption_extractor = ImageCaptionExtractor()

        # Create a test image
        self.test_image_path = "test_image.jpg"
        test_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
        test_image = Image.fromarray(test_array, mode="RGB")
        test_image.save(self.test_image_path)

    def tearDown(self):
        """Clean up test fixtures."""
        if Path(self.test_image_path).exists():
            Path(self.test_image_path).unlink()

    def test_extract_caption(self):
        """Test caption extraction."""
        caption = self.caption_extractor.extract_caption(
            image_path=self.test_image_path,
            use_mllm=False
        )

        # Check caption is returned
        self.assertIsInstance(caption, str)
        self.assertGreater(len(caption), 0)

    def test_extract_batch_captions(self):
        """Test batch caption extraction."""
        # Create multiple test images
        image_paths = []
        for i in range(3):
            path = f"test_image_{i}.jpg"
            test_array = np.random.randint(0, 255, (100, 100, 3), dtype=np.uint8)
            test_image = Image.fromarray(test_array, mode="RGB")
            test_image.save(path)
            image_paths.append(path)

        try:
            captions = self.caption_extractor.extract_batch_captions(
                image_paths=image_paths,
                use_mllm=False
            )

            # Check batch captions
            self.assertEqual(len(captions), 3)
            self.assertTrue(all(isinstance(c, str) for c in captions))
        finally:
            # Clean up
            for path in image_paths:
                Path(path).unlink()


if __name__ == "__main__":
    unittest.main()
