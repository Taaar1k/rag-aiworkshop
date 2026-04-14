import os
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import Optional
from pathlib import Path

class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )

    # LLM Endpoint
    llm_endpoint: str = "http://localhost:8080/v1/chat/completions"
    llm_model_name: str = "Qwen3-Coder-Next-APEX-Compact"
    llm_timeout: int = 30
    llm_max_tokens: int = 1024

    # Embeddings Endpoint
    embedding_endpoint: str = "http://localhost:8090/v1/embeddings"
    embedding_model_name: str = "nomic-embed-text-v1.5"
    embedding_timeout: int = 15

    # Retrieval Settings
    top_k: int = 5
    hybrid_search: bool = True
    rerank: bool = True
    chunk_size: int = 512
    chunk_overlap: int = 50

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Optional: Override via config files (future-proofing)
    config_file: Optional[str] = None

    @classmethod
    def load_from_yaml(cls, path: str = "config/default.yaml"):
        """Load settings from YAML file (if exists)"""
        import yaml
        path = Path(path)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
                return cls(**config)
        return cls()

# Global instance
settings = Settings.load_from_yaml()