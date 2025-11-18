"""Configuration helpers for the Wargame MCP tooling."""

from __future__ import annotations

from dataclasses import dataclass
import os
from pathlib import Path


@dataclass(slots=True)
class Settings:
    """Runtime configuration for the ingestion and query utilities."""

    chroma_path: Path = Path(os.getenv("CHROMA_PATH", "./data/chroma"))
    chroma_collection: str = os.getenv("CHROMA_COLLECTION", "wargame_docs")
    embedding_model: str = os.getenv("EMBEDDING_MODEL", "text-embedding-3-large")
    openai_api_key: str | None = os.getenv("OPENAI_API_KEY")
    openai_base_url: str | None = os.getenv("OPENAI_BASE_URL")

    # Mem0 configuration
    mem0_base_url: str | None = os.getenv("MEM0_BASE_URL")
    mem0_api_key: str | None = os.getenv("MEM0_API_KEY")
    mem0_default_limit: int = int(os.getenv("MEM0_DEFAULT_LIMIT", "10"))
    mem0_default_scope: str = os.getenv("MEM0_DEFAULT_SCOPE", "user")

    @property
    def chroma_path_str(self) -> str:
        return str(self.chroma_path)


SETTINGS = Settings()
