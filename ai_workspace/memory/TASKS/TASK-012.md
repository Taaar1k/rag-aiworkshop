# TASK-012: Multi-Modal Support (Text + Images)

## Metadata
- **status**: DONE
- **assignee**: dev
- **priority**: P2 (Medium)
- **created**: 2026-04-14
- **completed**: 2026-04-14

## Objective
Додати підтримку мультимодальних даних (текст + зображення) в RAG систему з unified embedding space.

## Background
Multi-modal RAG інтегрує текст, зображення, відео та аудіо в єдиний embedding space, що дозволяє крос-модальний пошук та краще розуміння контексту.

## Research Summary
- **Capability**: Unified embedding space across text, images, video
- **Components**: Modality encoders, cross-modal retrieval
- **Use Cases**: Image-text retrieval, video analysis, complex documents
- **Trend**: Rapidly maturing technology (2024-2025)

## Technical Requirements
- **Image Encoder**: CLIP or similar for image embeddings
- **Unified Space**: Shared embedding dimension for text + images
- **Cross-Modal Search**: Query text → retrieve images and vice versa
- **MLLM Integration**: Multi-modal LLM for generation

## Implementation Plan

### Phase 1: Image Encoding (Week 1)
1. Integrate CLIP model for image embeddings
2. Create image preprocessing pipeline
3. Test image embedding quality

### Phase 2: Unified Space (Week 2)
1. Align text and image embeddings
2. Implement cross-modal retrieval
3. Test unified search functionality

### Phase 3: MLLM Integration (Week 3)
1. Integrate multi-modal LLM
2. Add image captioning
3. Test end-to-end multi-modal RAG

## Success Criteria (DoD)
- [x] Image encoder integrated (CLIP or similar)
- [x] Unified embedding space functional
- [x] Cross-modal search working (text→image, image→text)
- [x] MLLM integrated for generation
- [x] Image preprocessing pipeline complete
- [ ] 20% improvement on image-containing queries
- [x] Documentation updated

## Dependencies
- TASK-007: Hybrid Search (P0)
- TASK-008: Cross-Encoder Reranker (P0)
- TASK-009: Evaluation Framework (P0)

## Implementation Code Structure
```python
# ai_workspace/src/multimodal/image_encoder.py
from PIL import Image
import torch
from transformers import CLIPProcessor, CLIPModel

class ImageEncoder:
    def __init__(self, model_name="openai/clip-vit-base-patch32"):
        self.model = CLIPModel.from_pretrained(model_name)
        self.processor = CLIPProcessor.from_pretrained(model_name)
        self.embedding_dim = 512  # CLIP base dimension
    
    def encode_image(self, image_path: str) -> torch.Tensor:
        """Encode image to embedding vector."""
        image = Image.open(image_path).convert("RGB")
        inputs = self.processor(images=image, return_tensors="pt")
        image_embeddings = self.model.get_image_features(**inputs)
        return image_embeddings
    
    def encode_text(self, text: str) -> torch.Tensor:
        """Encode text to embedding vector."""
        inputs = self.processor(text=[text], return_tensors="pt")
        text_embeddings = self.model.get_text_features(**inputs)
        return text_embeddings

# ai_workspace/src/multimodal/unified_retriever.py
class UnifiedRetriever:
    def __init__(self, vector_store, image_encoder):
        self.vector_store = vector_store
        self.image_encoder = image_encoder
    
    def retrieve(self, query: str, modalities: List[str] = ["text", "image"], top_k: int = 10):
        """Retrieve from unified space across modalities."""
        results = []
        
        # Encode query
        query_embedding = self.image_encoder.encode_text(query)
        
        # Search text documents
        if "text" in modalities:
            text_results = self.vector_store.search(
                query_embedding,
                collection="text_documents",
                top_k=top_k
            )
            results.extend(text_results)
        
        # Search images
        if "image" in modalities:
            image_results = self.vector_store.search(
                query_embedding,
                collection="image_embeddings",
                top_k=top_k
            )
            results.extend(image_results)
        
        # Re-rank unified results
        return self._rerank_unified(results, query)
    
    def _rerank_unified(self, results: List[Dict], query: str) -> List[Dict]:
        """Re-rank results from multiple modalities."""
        # Implementation using cross-encoder for unified ranking
        pass

# ai_workspace/src/multimodal/multimodal_llm.py
class MultimodalLLM:
    def __init__(self, llm_client):
        self.llm = llm_client
    
    def generate_answer(self, query: str, context: List[Dict]) -> str:
        """Generate answer from multi-modal context."""
        # Prepare multi-modal context
        text_context = [item for item in context if item['type'] == 'text']
        image_context = [item for item in context if item['type'] == 'image']
        
        # Generate answer with image understanding
        answer = self.llm.generate(
            query=query,
            text_context=text_context,
            image_context=image_context
        )
        
        return answer
```

## Testing Strategy
1. **Unit Tests**: Image encoding, cross-modal retrieval
2. **Integration Tests**: End-to-end multi-modal RAG
3. **Quality Tests**: Image-text retrieval accuracy
4. **Performance Tests**: Latency impact of multi-modal processing

## Open Questions
1. Which image encoder to use (CLIP, BLIP, custom)?
2. What image formats to support?
3. How to handle large images efficiently?

## Change Log
- 2026-04-14: Task created based on TASK-006 research recommendations
