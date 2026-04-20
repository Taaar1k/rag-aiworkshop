"""
Tests for Multi-Modal Support: Multimodal LLM
"""

import unittest
from unittest.mock import Mock, MagicMock

from multimodal.multimodal_llm import MultimodalLLM


class TestMultimodalLLM(unittest.TestCase):
    """Test cases for MultimodalLLM."""

    def setUp(self):
        """Set up test fixtures."""
        # Create mock LLM client
        self.mock_llm = Mock()
        self.mock_llm.generate = Mock(return_value="Generated answer")

        self.multimodal_llm = MultimodalLLM(llm_client=self.mock_llm)

    def test_llm_initialization(self):
        """Test LLM initialization."""
        self.assertIsNotNone(self.multimodal_llm.llm)

    def test_generate_answer(self):
        """Test answer generation from multi-modal context."""
        query = "What is in this image?"
        context = [
            {
                "type": "text",
                "content": "This is a text passage",
                "id": "text_1"
            },
            {
                "type": "image",
                "content": "image.jpg",
                "description": "An image of a cat"
            }
        ]

        answer = self.multimodal_llm.generate_answer(
            query=query,
            context=context
        )

        # Check answer is returned
        self.assertIsInstance(answer, str)
        self.assertEqual(answer, "Generated answer")

        # Check LLM generate was called
        self.mock_llm.generate.assert_called_once()

    def test_generate_with_image_understanding(self):
        """Test generation with image understanding."""
        query = "Describe this image"
        image_path = "test_image.jpg"

        answer = self.multimodal_llm.generate_with_image_understanding(
            query=query,
            image_path=image_path
        )

        self.assertIsInstance(answer, str)

    def test_caption_image(self):
        """Test image captioning."""
        image_path = "test_image.jpg"

        caption = self.multimodal_llm.caption_image(
            image_path=image_path,
            prompt="Describe the main subject"
        )

        self.assertIsInstance(caption, str)

    def test_compare_images(self):
        """Test image comparison."""
        image_path_1 = "image1.jpg"
        image_path_2 = "image2.jpg"

        comparison = self.multimodal_llm.compare_images(
            image_path_1=image_path_1,
            image_path_2=image_path_2,
            comparison_aspect="color distribution"
        )

        self.assertIsInstance(comparison, str)

    def test_build_multimodal_prompt(self):
        """Test prompt building for multi-modal generation."""
        query = "What is shown in the image?"
        text_context = [
            {"content": "Text passage 1"},
            {"content": "Text passage 2"}
        ]
        image_context = [
            {"description": "Image of a cat"}
        ]

        # Access private method for testing
        prompt = self.multimodal_llm._build_multimodal_prompt(
            query=query,
            text_context=text_context,
            image_context=image_context,
            system_prompt="You are helpful"
        )

        # Check prompt contains expected elements
        self.assertIn("System: You are helpful", prompt)
        self.assertIn("Image of a cat", prompt)
        self.assertIn("Text passage 1", prompt)
        self.assertIn("Text passage 2", prompt)
        self.assertIn(query, prompt)


if __name__ == "__main__":
    unittest.main()
