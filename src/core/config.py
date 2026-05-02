import logging
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field
from typing import Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Endpoint (required)
    llm_endpoint: str = Field(default="http://localhost:8080/v1/chat/completions")
    llm_model_name: str = "Qwen3-Coder-Next-APEX-Compact"
    llm_timeout: int = Field(default=30, ge=1, le=300)
    llm_max_tokens: int = Field(default=1024, ge=1, le=8192)

    # Embeddings Endpoint
    embedding_endpoint: str = Field(default="http://localhost:8090/v1/embeddings")
    embedding_model_name: str = "nomic-embed-text-v1.5"
    embedding_timeout: int = Field(default=15, ge=1, le=60)

    # Retrieval Settings
    top_k: int = Field(default=5, ge=1, le=100)
    hybrid_search: bool = True
    rerank: bool = True
    chunk_size: int = Field(default=512, ge=100, le=2048)
    chunk_overlap: int = Field(default=50, ge=0, le=512)

    # Server
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)

    # Optional: Override via config files
    config_file: Optional[str] = None

    def validate_required(self) -> bool:
        """Validate required environment variables."""
        required = ["llm_endpoint"]
        missing = [k for k in required if not getattr(self, k, None)]
        if missing:
            logger.warning(f"Missing required config: {missing}")
            return False
        return True

    @classmethod
    def load_from_yaml(cls, path: str = "config/default.yaml"):
        """Load settings from YAML file (if exists)"""
        import yaml
        p = Path(path)
        if p.exists():
            with open(p, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return cls(**config)
        return cls()


# Global instance
settings = Settings.load_from_yaml()