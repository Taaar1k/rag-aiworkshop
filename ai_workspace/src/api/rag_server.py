"""
Shared RAG Server with FastAPI and Qdrant integration.
Provides OpenAI-compatible endpoints for RAG operations.
"""

import os
import sys
import logging
import yaml
import asyncio
from typing import List, Dict, Optional, Any
from pathlib import Path
from datetime import datetime
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field
import qdrant_client
from qdrant_client.models import VectorParams, Distance, PointStruct
from slowapi.errors import RateLimitExceeded

# Add src to path for imports
sys.path.append(str(Path(__file__).parent.parent.parent))

try:
    from core.config import Settings
except ImportError:
    from ..core.config import Settings

# Import rate limiter
from .rate_limiter import limiter, rate_limit_exceeded_handler

# Import health checker
from .health_check import health_checker

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load embedding config
_embedding_config_path = Path(__file__).parent.parent.parent / "config" / "embedding_config.yaml"
EMBEDDING_CONFIG = {}
if _embedding_config_path.exists():
    with open(_embedding_config_path, "r", encoding="utf-8") as f:
        content = f.read()
        # Render template variables {{port}}
        port = os.getenv("EMBEDDING_PORT", "8090")
        content = content.replace("{{port}}", port)
        EMBEDDING_CONFIG = yaml.safe_load(content) or {}

# Determine embedding source from config or env: "local_api" or "sentence_transformers"
EMBEDDING_SOURCE = os.getenv("EMBEDDING_SOURCE", "local_api")
from .scanner_manager import (
    initialize_scanner,
    start_scanner,
    stop_scanner,
    router as scanner_router,
)

# Load config for scanner
_config_path = Path(__file__).parent.parent.parent / "config" / "default.yaml"
_dir_scan_config = {}
if _config_path.exists():
    with open(_config_path, "r", encoding="utf-8") as f:
        _cfg = yaml.safe_load(f)
        _dir_scan_config = _cfg.get("directory_scanning", {})


@asynccontextmanager
async def lifespan(app_fastapi: FastAPI):
    logger.info("RAG server lifespan startup...")
    
    # Initialize scanner
    await initialize_scanner(_dir_scan_config)
    await start_scanner()
    
    # Initialize services into app.state
    app_fastapi.state.qdrant = initialize_qdrant()
    
    embeddings = initialize_embedding_model()
    app_fastapi.state.embeddings = embeddings
    
    app_fastapi.state.llm = initialize_llm_model()
    
    yield
    
    logger.info("RAG server lifespan shutdown...")
    await stop_scanner()
    
    if app_fastapi.state.qdrant:
        app_fastapi.state.qdrant.close()


# Initialize FastAPI app with lifespan
app = FastAPI(
    title="Shared RAG API",
    description="OpenAI-compatible RAG server with Qdrant vector storage",
    version="1.0.0",
    lifespan=lifespan,
)

# Add CORS middleware — env-driven whitelist (SPEC-2026-04-20-PRODUCTION-HARDENING)
CORS_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:3000,http://localhost:5173").split(",")

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limit exception handler
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


# Global catch-all: sanitize unexpected exceptions to 500 (TASK-039)
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all exception handler — logs with traceback, returns sanitized 500."""
    logger.exception("Unhandled exception")
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error"},
    )

# Add slowapi state for rate limit tracking
app.state.limiter = limiter

# Include scanner router
app.include_router(scanner_router, prefix="/scanner", tags=["scanner"])

# Global instances
settings = Settings()


def get_qdrant():
    """Get Qdrant client from app state."""
    return getattr(app.state, "qdrant", None)


def get_embeddings():
    """Get embedding model config from app state."""
    return getattr(app.state, "embeddings", None)


def get_llm():
    """Get LLM model from app state."""
    return getattr(app.state, "llm", None)


# Pydantic Models for OpenAI-compatible API
class Message(BaseModel):
    role: str
    content: str


class ChatCompletionRequest(BaseModel):
    model: str = "shared-rag-v1"
    messages: List[Message]
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    top_p: float = Field(default=1.0, ge=0.0, le=1.0)
    n: int = Field(default=1, ge=1, le=10)
    max_tokens: int = Field(default=512, ge=1, le=4096)
    stream: bool = False
    stop: Optional[List[str]] = None
    presence_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)
    frequency_penalty: float = Field(default=0.0, ge=-2.0, le=2.0)


class ChatCompletionResponse(BaseModel):
    id: str
    object: str = "chat.completion"
    created: int
    model: str
    choices: List[Dict[str, Any]]
    usage: Dict[str, int]


class EmbeddingRequest(BaseModel):
    model: str = "nomic-embed-text-v1.5"
    input: str | List[str]
    encoding_format: str = "float"


class EmbeddingResponse(BaseModel):
    object: str = "list"
    data: List[Dict[str, Any]]
    model: str
    usage: Dict[str, int]


class Document(BaseModel):
    id: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class RAGQueryRequest(BaseModel):
    query: str
    top_k: int = Field(default=5, ge=1, le=100)
    filters: Optional[Dict[str, Any]] = None
    temperature: float = Field(default=0.7, ge=0.0, le=1.0)
    max_tokens: int = Field(default=512, ge=1, le=4096)


class RAGQueryResponse(BaseModel):
    answer: str
    sources: List[Dict[str, Any]]
    metadata: Dict[str, Any]


# Health check endpoints (exempt from rate limiting)
@app.get("/health")
@limiter.exempt
async def health_check(request: Request):
    """Lightweight health check (uses cache)."""
    health = await health_checker.get_overall_health(verbose=False)
    return health


@app.get("/health/verbose")
@limiter.exempt
async def health_check_verbose(request: Request):
    """Detailed health check (no cache, checks all components)."""
    health = await health_checker.get_overall_health(verbose=True)
    health["cache_enabled"] = False
    return health


@app.get("/metrics")
@limiter.exempt
async def metrics(request: Request):
    """Prometheus-compatible metrics endpoint."""
    health = await health_checker.get_overall_health(verbose=False)
    metrics_output = health_checker.get_prometheus_metrics(health)
    return JSONResponse(content=metrics_output, media_type="text/plain")


# Rate limit status endpoint
@app.get("/rate-limit-status")
@limiter.exempt
async def rate_limit_status(request: Request):
    """Get current rate limit status for the caller."""
    return {
        "limit": getattr(request.state, 'rate_limit', None),
        "remaining": getattr(request.state, 'rate_limit_remaining', None),
        "reset": getattr(request.state, 'rate_limit_reset', None)
    }


# OpenAI-compatible endpoints
@app.post("/v1/chat/completions")
@limiter.limit("1000 per minute")
async def chat_completions(request: Request, body: ChatCompletionRequest):
    """
    OpenAI-compatible endpoint for chat completions with RAG.
    Uses Qdrant for vector search and LLM for response generation.
    """
    # Validate messages
    if not body.messages:
        raise HTTPException(status_code=422, detail="messages field is required and cannot be empty")
    
    # Extract query from messages
    query = body.messages[-1].content if body.messages else ""
    
    # Perform RAG query
    rag_response = perform_rag_query(
        query=query,
        top_k=body.top_k if hasattr(body, 'top_k') else 5,
        temperature=body.temperature
    )
    
    return ChatCompletionResponse(
        id=f"chatcmpl-{int(datetime.now().timestamp())}",
        created=int(datetime.now().timestamp()),
        model=body.model,
        choices=[{
            "index": 0,
            "message": {
                "role": "assistant",
                "content": rag_response["answer"]
            },
            "finish_reason": "stop"
        }],
        usage={
            "prompt_tokens": len(query.split()),
            "completion_tokens": len(rag_response["answer"].split()),
            "total_tokens": len(query.split()) + len(rag_response["answer"].split())
        }
    )


@app.post("/v1/embeddings")
@limiter.limit("1000 per minute")
async def create_embeddings(request: Request, body: EmbeddingRequest):
    """
    OpenAI-compatible endpoint for embedding generation.
    Uses sentence-transformers for embedding generation.
    """
    inputs = body.input if isinstance(body.input, list) else [body.input]
    
    # Generate embeddings
    embeddings = []
    for text in inputs:
        embedding = generate_embedding(text)
        embeddings.append({
            "object": "embedding",
            "embedding": embedding,
            "index": len(embeddings)
        })
    
    return EmbeddingResponse(
        object="list",
        data=embeddings,
        model=body.model,
        usage={
            "prompt_tokens": sum(len(text.split()) for text in inputs),
            "total_tokens": sum(len(text.split()) for text in inputs)
        }
    )


# RAG-specific endpoints
@app.post("/rag/query")
@limiter.limit("1000 per minute")
async def rag_query(request: Request, body: RAGQueryRequest):
    """
    Custom RAG query endpoint with vector search and LLM generation.
    """
    response = perform_rag_query(
        query=body.query,
        top_k=body.top_k,
        temperature=body.temperature
    )
    return response


@app.post("/rag/index")
@limiter.limit("1000 per minute")
async def index_document(request: Request, document: Document):
    """Index a document into the vector store."""
    try:
        embedding = generate_embedding(document.text)
        qdrant = get_qdrant()
        
        if qdrant is None:
            raise HTTPException(status_code=503, detail="Vector store not available")
        
        def _upsert():
            qdrant.upsert(
                collection_name="rag_documents",
                points=[PointStruct(
                    id=document.id,
                    vector=embedding,
                    payload={
                        "text": document.text,
                        **document.metadata
                    }
                )]
            )
        
        await asyncio.to_thread(_upsert)
        
        return {"status": "success", "document_id": document.id}
    except HTTPException:
        raise
    except Exception:
        logger.exception("Error indexing document")
        raise HTTPException(status_code=500, detail="Internal server error")


# Utility functions
def initialize_qdrant():
    """Initialize Qdrant client and create collection if not exists.
    
    Returns None if Qdrant is not available (graceful degradation).
    """
    try:
        host = os.getenv("QDRANT_HOST", "localhost")
        port = int(os.getenv("QDRANT_PORT", 6333))
        
        client = qdrant_client.QdrantClient(host=host, port=port)
        
        collection_name = "rag_documents"
        if not client.collection_exists(collection_name):
            client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=768,
                    distance=Distance.COSINE
                )
            )
        logger.info(f"Initialized Qdrant client at {host}:{port}")
        
        return client
    except Exception:
        logger.warning("Qdrant initialization failed, running in offline mode", exc_info=True)
        return None


def initialize_embedding_model():
    """Initialize embedding model (local API or sentence-transformers based on config)."""
    use_local_api = EMBEDDING_SOURCE == "local_api"
    
    if use_local_api:
        # Use local llama.cpp API
        model_config = EMBEDDING_CONFIG.get("model", {})
        endpoint = model_config.get("endpoint", "http://localhost:8090/v1/embeddings")
        timeout = model_config.get("timeout", 15)
        
        logger.info(f"Using local embedding API: {endpoint}")
        return {"type": "api", "endpoint": endpoint, "timeout": timeout}
    else:
        # Use sentence-transformers
        try:
            from sentence_transformers import SentenceTransformer
            # Use nomic for consistency with API (768 dims)
            model_name = os.getenv("EMBEDDING_MODEL", "nomic-ai/nomic-embed-text-v1.5")
            model = SentenceTransformer(model_name, trust_remote_code=True)
            logger.info(f"Initialized sentence-transformers model: {model_name}")
            return {"type": "transformers", "model": model}
        except Exception as e:
            logger.warning(f"Embedding model init failed: {e}")
            return None


def generate_embedding(text: str) -> List[float]:
    """Generate embedding via local API or sentence-transformers."""
    embeddings = get_embeddings()
    if embeddings is None:
        raise RuntimeError("Embedding model not available")
    
    if embeddings.get("type") == "api":
        # Use local API
        import httpx
        endpoint = embeddings["endpoint"]
        timeout = embeddings.get("timeout", 15)
        
        try:
            with httpx.Client(timeout=timeout) as client:
                response = client.post(
                    endpoint,
                    json={"input": text, "model": "nomic-embed-text-v1.5"}
                )
                response.raise_for_status()
                data = response.json()
                return data["data"][0]["embedding"]
        except Exception as e:
            logger.error(f"Embedding API failed: {e}")
            raise RuntimeError(f"Embedding API failed: {e}")
    else:
        # Use sentence-transformers
        model = embeddings.get("model")
        embedding = model.encode(text)
        return embedding.tolist()


def initialize_llm_model():
    """Initialize GGUF model via llama.cpp."""
    try:
        from llama_cpp import Llama
        
        model_path = os.getenv("LLM_MODEL_PATH", "models/llm/default.gguf")
        
        model = Llama(
            model_path=model_path,
            n_ctx=2048,
            n_threads=4,
            n_gpu_layers=0
        )
        
        logger.info(f"Initialized LLM model: {model_path}")
        return model
    except Exception:
        logger.warning("LLM initialization failed, using fallback", exc_info=True)
        return None


def perform_rag_query(query: str, top_k: int = 5, temperature: float = 0.7) -> Dict[str, Any]:
    """Perform RAG query: vector search + LLM generation."""
    qdrant = get_qdrant()
    llm = get_llm()
    
    query_embedding = generate_embedding(query)
    
    search_results = []
    if qdrant:
        try:
            search_results = qdrant.search(
                collection_name="rag_documents",
                query_vector=query_embedding,
                limit=top_k
            )
        except Exception:
            logger.warning("Qdrant search failed, returning empty results", exc_info=True)
    
    context = "\n\n".join([hit.payload.get("text", "") for hit in search_results])
    sources = [
        {
            "id": hit.id,
            "score": hit.score,
            "text": hit.payload.get("text", "")[:200] + "..."
        }
        for hit in search_results
    ]
    
    if llm:
        prompt = f"""Context: {context}

Question: {query}

Answer:"""
        
        try:
            response = llm(
                prompt,
                max_tokens=512,
                temperature=temperature
            )
            answer = response["choices"][0]["text"].strip()
        except Exception:
            logger.warning("LLM generation failed, using fallback", exc_info=True)
            answer = f"Based on the retrieved documents:\n\n{context}\n\nQuestion: {query}"
    else:
        answer = f"Based on the retrieved documents:\n\n{context}\n\nQuestion: {query}"
    
    return {
        "answer": answer,
        "sources": sources,
        "metadata": {
            "timestamp": datetime.now().isoformat(),
            "query": query,
            "top_k": top_k
        }
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "rag_server:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
