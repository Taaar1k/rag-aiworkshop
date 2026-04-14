"""
Multi-Modal Support: Image Preprocessing Pipeline
"""

from typing import Optional, Dict, Any
from PIL import Image
import torch
import numpy as np
from pathlib import Path


class ImagePreprocessor:
    """
    Preprocessing pipeline for images before encoding.
    Handles resizing, normalization, format conversion, and quality optimization.
    """

    DEFAULT_TARGET_SIZE = (224, 224)
    DEFAULT_MEAN = [0.485, 0.456, 0.406]
    DEFAULT_STD = [0.229, 0.224, 0.225]

    SUPPORTED_FORMATS = {".jpg", ".jpeg", ".png", ".gif", ".bmp", ".webp", ".tiff"}

    def __init__(
        self,
        target_size: tuple = DEFAULT_TARGET_SIZE,
        normalize: bool = True,
        mean: list = DEFAULT_MEAN,
        std: list = DEFAULT_STD,
        max_size: Optional[int] = None,
        quality: int = 95
    ):
        """
        Initialize image preprocessor.

        Args:
            target_size: Target size for resizing (width, height)
            normalize: Whether to normalize images
            mean: Mean values for normalization (RGB)
            std: Standard deviation values for normalization (RGB)
            max_size: Maximum dimension for resizing (preserves aspect ratio)
            quality: JPEG quality for compression (1-100)
        """
        self.target_size = target_size
        self.normalize = normalize
        self.mean = mean
        self.std = std
        self.max_size = max_size
        self.quality = quality

    def preprocess(
        self,
        image_path: str,
        convert_to_rgb: bool = True
    ) -> Dict[str, Any]:
        """
        Preprocess an image for encoding.

        Args:
            image_path: Path to image file
            convert_to_rgb: Convert to RGB mode

        Returns:
            Dict with processed image, tensor, and metadata
        """
        # Load image
        image = Image.open(image_path)

        # Convert to RGB if needed
        if convert_to_rgb and image.mode != "RGB":
            image = image.convert("RGB")

        # Get original metadata
        original_size = image.size
        original_format = image.format

        # Resize image
        if self.max_size:
            image = self._resize_max(image)
        else:
            image = self._resize(image)

        # Convert to numpy array
        image_array = np.array(image)

        # Normalize if requested
        if self.normalize:
            image_array = self._normalize_array(image_array)

        # Convert to tensor
        image_tensor = self._array_to_tensor(image_array)

        return {
            "image": image,
            "tensor": image_tensor,
            "array": image_array,
            "original_size": original_size,
            "original_format": original_format,
            "processed_size": image.size
        }

    def preprocess_batch(
        self,
        image_paths: list[str],
        convert_to_rgb: bool = True
    ) -> list[Dict[str, Any]]:
        """
        Preprocess multiple images.

        Args:
            image_paths: List of image paths
            convert_to_rgb: Convert to RGB mode

        Returns:
            List of processed image dictionaries
        """
        return [
            self.preprocess(path, convert_to_rgb)
            for path in image_paths
        ]

    def _resize(self, image: Image.Image) -> Image.Image:
        """Resize image to target size."""
        return image.resize(self.target_size, Image.Resampling.LANCZOS)

    def _resize_max(self, image: Image.Image) -> Image.Image:
        """Resize image to fit within max_size while preserving aspect ratio."""
        width, height = image.size
        max_dim = max(width, height)

        if max_dim > self.max_size:
            scale = self.max_size / max_dim
            new_width = int(width * scale)
            new_height = int(height * scale)
            return image.resize((new_width, new_height), Image.Resampling.LANCZOS)

        return image

    def _normalize_array(self, array: np.ndarray) -> np.ndarray:
        """Normalize image array using mean and std."""
        # Ensure array is in range [0, 1]
        if array.max() > 1:
            array = array / 255.0

        # Normalize using mean and std
        for i in range(3):
            array[:, :, i] = (array[:, :, i] - self.mean[i]) / self.std[i]

        return array

    def _array_to_tensor(self, array: np.ndarray) -> torch.Tensor:
        """Convert numpy array to PyTorch tensor."""
        # Convert from HWC to CHW format
        tensor = torch.from_numpy(array).permute(2, 0, 1).float()
        return tensor

    def optimize_for_storage(
        self,
        image_path: str,
        output_path: Optional[str] = None
    ) -> str:
        """
        Optimize image for storage (compression, format conversion).

        Args:
            image_path: Path to source image
            output_path: Path to save optimized image (optional)

        Returns:
            str: Path to optimized image
        """
        image = Image.open(image_path)

        # Determine output path
        if output_path is None:
            base, _ = Path(image_path).name.rsplit(".", 1)
            output_path = f"{base}_optimized.jpg"

        # Save with optimization
        image.save(output_path, "JPEG", quality=self.quality, optimize=True)

        return output_path

    def extract_metadata(
        self,
        image_path: str
    ) -> Dict[str, Any]:
        """
        Extract metadata from image.

        Args:
            image_path: Path to image

        Returns:
            Dict with image metadata
        """
        image = Image.open(image_path)

        return {
            "path": image_path,
            "format": image.format,
            "mode": image.mode,
            "size": image.size,
            "width": image.width,
            "height": image.height,
            "file_size": Path(image_path).stat().st_size if Path(image_path).exists() else 0
        }


class ImageCaptionExtractor:
    """
    Extract captions/descriptions from images using simple heuristics.
    Can be extended with MLLM for better captions.
    """

    def __init__(self, multimodal_llm=None):
        """
        Initialize caption extractor.

        Args:
            multimodal_llm: Optional MultimodalLLM instance for advanced captioning
        """
        self.multimodal_llm = multimodal_llm

    def extract_caption(
        self,
        image_path: str,
        use_mllm: bool = True
    ) -> str:
        """
        Extract caption for an image.

        Args:
            image_path: Path to image
            use_mllm: Use MLLM for captioning (requires multimodal_llm)

        Returns:
            str: Generated caption
        """
        if use_mllm and self.multimodal_llm:
            return self.multimodal_llm.caption_image(image_path)
        else:
            # Simple heuristic-based caption
            return self._simple_caption(image_path)

    def _simple_caption(self, image_path: str) -> str:
        """
        Generate simple caption based on image metadata.

        Args:
            image_path: Path to image

        Returns:
            str: Simple caption
        """
        from PIL import Image
        from pathlib import Path

        image = Image.open(image_path)
        path = Path(image_path)

        caption = f"Image of size {image.size[0]}x{image.size[1]}, format {image.format}, file {path.name}"

        return caption

    def extract_batch_captions(
        self,
        image_paths: list[str],
        use_mllm: bool = True
    ) -> list[str]:
        """
        Extract captions for multiple images.

        Args:
            image_paths: List of image paths
            use_mllm: Use MLLM for captioning

        Returns:
            List of captions
        """
        return [
            self.extract_caption(path, use_mllm)
            for path in image_paths
        ]
