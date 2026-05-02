"""
Multi-Modal Support Package
Provides unified embedding space for text and images in RAG systems.
"""

from .image_encoder import ImageEncoder
from .unified_retriever import UnifiedRetriever, RetrievalResult, ModalityType
from .multimodal_llm import MultimodalLLM
from .image_preprocessor import ImagePreprocessor, ImageCaptionExtractor

__all__ = [
    "ImageEncoder",
    "UnifiedRetriever",
    "RetrievalResult",
    "ModalityType",
    "MultimodalLLM",
    "ImagePreprocessor",
    "ImageCaptionExtractor",
]

__version__ = "0.1.0"
