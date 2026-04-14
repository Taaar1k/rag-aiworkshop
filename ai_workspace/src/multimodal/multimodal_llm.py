"""
Multi-Modal Support: Multi-Modal LLM for Generation
"""

from typing import List, Dict, Optional, Union
import torch


class MultimodalLLM:
    """
    Multi-modal LLM for generating answers from text and image context.
    Integrates with existing LLM client for generation.
    """

    def __init__(self, llm_client):
        """
        Initialize multimodal LLM.

        Args:
            llm_client: Existing LLM client instance for generation
        """
        self.llm = llm_client

    def generate_answer(
        self,
        query: str,
        context: List[Dict],
        system_prompt: Optional[str] = None
    ) -> str:
        """
        Generate answer from multi-modal context.

        Args:
            query: User query
            context: List of context items (text and/or images)
            system_prompt: Optional system prompt for the LLM

        Returns:
            str: Generated answer
        """
        # Separate text and image context
        text_context = [item for item in context if item.get("type") == "text"]
        image_context = [item for item in context if item.get("type") == "image"]

        # Build multi-modal prompt
        prompt = self._build_multimodal_prompt(
            query=query,
            text_context=text_context,
            image_context=image_context,
            system_prompt=system_prompt
        )

        # Generate answer using LLM
        answer = self.llm.generate(prompt=prompt)

        return answer

    def _build_multimodal_prompt(
        self,
        query: str,
        text_context: List[Dict],
        image_context: List[Dict],
        system_prompt: Optional[str]
    ) -> str:
        """
        Build prompt for multi-modal generation.

        Args:
            query: User query
            text_context: Text context items
            image_context: Image context items
            system_prompt: System prompt

        Returns:
            str: Formatted prompt
        """
        # Build system prompt
        if system_prompt:
            prompt_parts = [f"System: {system_prompt}\n"]
        else:
            prompt_parts = ["System: You are a helpful assistant that can analyze both text and images.\n"]

        # Add image descriptions
        if image_context:
            prompt_parts.append("Here are relevant images and their descriptions:\n")
            for i, img in enumerate(image_context, 1):
                description = img.get("description", "Image content")
                prompt_parts.append(f"  Image {i}: {description}\n")
            prompt_parts.append("\n")

        # Add text context
        if text_context:
            prompt_parts.append("Here are relevant text passages:\n")
            for i, text in enumerate(text_context, 1):
                content = text.get("content", "")
                prompt_parts.append(f"  Passage {i}: {content}\n")
            prompt_parts.append("\n")

        # Add user query
        prompt_parts.append(f"User: {query}\n")
        prompt_parts.append("Assistant: ")

        return "".join(prompt_parts)

    def generate_with_image_understanding(
        self,
        query: str,
        image_path: str,
        additional_text_context: Optional[List[str]] = None
    ) -> str:
        """
        Generate answer with specific image understanding.

        Args:
            query: User query
            image_path: Path to image to analyze
            additional_text_context: Optional additional text context

        Returns:
            str: Generated answer with image understanding
        """
        # Build context
        context = [
            {
                "type": "image",
                "content": image_path,
                "description": f"Image at {image_path}"
            }
        ]

        if additional_text_context:
            for i, text in enumerate(additional_text_context, 1):
                context.append({
                    "type": "text",
                    "content": text,
                    "id": f"text_{i}"
                })

        return self.generate_answer(query=query, context=context)

    def caption_image(
        self,
        image_path: str,
        prompt: Optional[str] = None
    ) -> str:
        """
        Generate caption for an image.

        Args:
            image_path: Path to image
            prompt: Optional custom prompt for captioning

        Returns:
            str: Generated caption
        """
        system_prompt = "You are an image captioning assistant. Describe the image in detail."
        if prompt:
            system_prompt = f"{system_prompt} Use the following guidance: {prompt}"

        context = [
            {
                "type": "image",
                "content": image_path,
                "description": f"Image to caption: {image_path}"
            }
        ]

        query = "Describe this image in detail."
        return self.generate_answer(query=query, context=context, system_prompt=system_prompt)

    def compare_images(
        self,
        image_path_1: str,
        image_path_2: str,
        comparison_aspect: Optional[str] = None
    ) -> str:
        """
        Compare two images and describe similarities/differences.

        Args:
            image_path_1: Path to first image
            image_path_2: Path to second image
            comparison_aspect: Optional specific aspect to compare

        Returns:
            str: Comparison description
        """
        system_prompt = "You are an image comparison assistant. Analyze and compare the two images."
        if comparison_aspect:
            system_prompt = f"{system_prompt} Focus on: {comparison_aspect}"

        context = [
            {
                "type": "image",
                "content": image_path_1,
                "description": f"First image: {image_path_1}"
            },
            {
                "type": "image",
                "content": image_path_2,
                "description": f"Second image: {image_path_2}"
            }
        ]

        query = "Compare these two images and describe their similarities and differences."
        return self.generate_answer(query=query, context=context, system_prompt=system_prompt)
