"""
Multi-Modal Support: Image Encoder using CLIP
"""

from typing import Optional
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel


class ImageEncoder:
    """
    CLIP-based image encoder for multi-modal RAG.
    Provides unified embedding space for text and images.
    """

    DEFAULT_MODEL = "openai/clip-vit-base-patch32"

    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: Optional[str] = None,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize CLIP image encoder.

        Args:
            model_name: Hugging Face model name for CLIP
            device: Device to run model on ('cuda', 'cpu', or None for auto)
            cache_dir: Custom cache directory for models
        """
        self.model_name = model_name
        self.cache_dir = cache_dir

        # Auto-detect device
        if device is None:
            self.device = "cuda" if torch.cuda.is_available() else "cpu"
        else:
            self.device = device

        # Load model and processor
        self.model = CLIPModel.from_pretrained(
            model_name,
            cache_dir=cache_dir
        ).to(self.device)

        self.processor = CLIPProcessor.from_pretrained(
            model_name,
            cache_dir=cache_dir
        )

        # CLIP base model embedding dimension
        self.embedding_dim = 512

        # Set to evaluation mode
        self.model.eval()

    def encode_image(
        self,
        image_path: str,
        normalize: bool = True
    ) -> torch.Tensor:
        """
        Encode an image to embedding vector.

        Args:
            image_path: Path to image file
            normalize: Whether to L2-normalize the embedding

        Returns:
            torch.Tensor: Image embedding vector of shape (embedding_dim,)
        """
        # Load and preprocess image
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt").to(self.device)

        # Get image features
        with torch.no_grad():
            outputs = self.model.get_image_features(**inputs)
            # CLIP uses pooler_output for the final embedding (shape: [batch, 512])
            if hasattr(outputs, 'pooler_output'):
                image_embeddings = outputs.pooler_output
            elif hasattr(outputs, 'image_embeds'):
                image_embeddings = outputs.image_embeds
            else:
                image_embeddings = outputs

        # Normalize if requested
        if normalize:
            image_embeddings = torch.nn.functional.normalize(image_embeddings, dim=-1)

        # Return as 1D tensor
        return image_embeddings.squeeze(0)

    def encode_text(
        self,
        text: str,
        normalize: bool = True
    ) -> torch.Tensor:
        """
        Encode text to embedding vector using CLIP text encoder.

        Args:
            text: Text string to encode
            normalize: Whether to L2-normalize the embedding

        Returns:
            torch.Tensor: Text embedding vector of shape (embedding_dim,)
        """
        # Process text
        inputs = self.processor(text=[text], return_tensors="pt").to(self.device)

        # Get text features directly from CLIP model
        with torch.no_grad():
            outputs = self.model.get_text_features(**inputs)
            # CLIP uses pooler_output for the final embedding (shape: [batch, 512])
            if hasattr(outputs, 'pooler_output'):
                text_embeddings = outputs.pooler_output
            elif hasattr(outputs, 'text_embeds'):
                text_embeddings = outputs.text_embeds
            else:
                text_embeddings = outputs

        # Normalize if requested (CLIP embeddings are already normalized by default)
        if normalize:
            text_embeddings = torch.nn.functional.normalize(text_embeddings, dim=-1)

        # Return as 1D tensor
        return text_embeddings.squeeze(0)

    def encode_batch_images(
        self,
        image_paths: list[str],
        normalize: bool = True
    ) -> torch.Tensor:
        """
        Encode multiple images to embedding vectors.

        Args:
            image_paths: List of image file paths
            normalize: Whether to L2-normalize the embeddings

        Returns:
            torch.Tensor: Batch of image embeddings of shape (batch_size, embedding_dim)
        """
        # Load and preprocess images
        images = [Image.open(path).convert("RGB") for path in image_paths]
        inputs = self.processor(images=images, return_tensors="pt").to(self.device)

        # Get image features directly from CLIP model
        with torch.no_grad():
            outputs = self.model.get_image_features(**inputs)
            # CLIP uses pooler_output for the final embedding (shape: [batch, 512])
            if hasattr(outputs, 'pooler_output'):
                image_embeddings = outputs.pooler_output
            elif hasattr(outputs, 'image_embeds'):
                image_embeddings = outputs.image_embeds
            else:
                image_embeddings = outputs

        # Normalize if requested (CLIP embeddings are already normalized by default)
        if normalize:
            image_embeddings = torch.nn.functional.normalize(image_embeddings, dim=-1)

        return image_embeddings

    def encode_batch_texts(
        self,
        texts: list[str],
        normalize: bool = True
    ) -> torch.Tensor:
        """
        Encode multiple texts to embedding vectors.

        Args:
            texts: List of text strings
            normalize: Whether to L2-normalize the embeddings

        Returns:
            torch.Tensor: Batch of text embeddings of shape (batch_size, embedding_dim)
        """
        # Process texts
        inputs = self.processor(text=texts, return_tensors="pt").to(self.device)

        # Get text features directly from CLIP model
        with torch.no_grad():
            outputs = self.model.get_text_features(**inputs)
            # CLIP uses pooler_output for the final embedding (shape: [batch, 512])
            if hasattr(outputs, 'pooler_output'):
                text_embeddings = outputs.pooler_output
            elif hasattr(outputs, 'text_embeds'):
                text_embeddings = outputs.text_embeds
            else:
                text_embeddings = outputs

        # Normalize if requested (CLIP embeddings are already normalized by default)
        if normalize:
            text_embeddings = torch.nn.functional.normalize(text_embeddings, dim=-1)

        return text_embeddings

    def compute_similarity(
        self,
        embedding1: torch.Tensor,
        embedding2: torch.Tensor
    ) -> torch.Tensor:
        """
        Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            torch.Tensor: Cosine similarity score
        """
        # Ensure embeddings are normalized
        emb1 = embedding1 / embedding1.norm() if embedding1.dim() == 1 else embedding1 / embedding1.norm(dim=-1)
        emb2 = embedding2 / embedding2.norm() if embedding2.dim() == 1 else embedding2 / embedding2.norm(dim=-1)

        # Compute similarity
        return torch.dot(emb1, emb2)

    def get_device(self) -> str:
        """Return the device being used for inference."""
        return self.device

    def __repr__(self) -> str:
        return (
            f"ImageEncoder(model={self.model_name}, "
            f"device={self.device}, embedding_dim={self.embedding_dim})"
        )
