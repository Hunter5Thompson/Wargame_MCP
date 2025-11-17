"""Embedding provider abstractions."""

from __future__ import annotations

import hashlib
from typing import Iterable

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency at runtime
    OpenAI = None  # type: ignore

from .config import SETTINGS


class EmbeddingProvider:
    def embed(self, texts: Iterable[str]) -> list[list[float]]:  # pragma: no cover - interface only
        raise NotImplementedError


class FakeEmbeddingProvider(EmbeddingProvider):
    """Deterministic hashing used for tests and offline workflows."""

    def __init__(self, dimensions: int = 1536) -> None:
        self.dimensions = dimensions

    def embed(self, texts: Iterable[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for text in texts:
            digest = hashlib.sha256(text.encode("utf-8")).digest()
            repeated = (digest * ((self.dimensions // len(digest)) + 1))[: self.dimensions]
            vector = [b / 255.0 for b in repeated]
            vectors.append(vector)
        return vectors


class OpenAIEmbeddingProvider(EmbeddingProvider):
    def __init__(self, model: str | None = None, api_key: str | None = None, base_url: str | None = None) -> None:
        if OpenAI is None:
            raise RuntimeError("openai package not installed; install openai>=1.0.0")
        self.model = model or SETTINGS.embedding_model
        api_key = api_key or SETTINGS.openai_api_key
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for real embeddings")
        self.client = OpenAI(api_key=api_key, base_url=base_url or SETTINGS.openai_base_url)

    def embed(self, texts: Iterable[str]) -> list[list[float]]:
        texts_list = list(texts)
        response = self.client.embeddings.create(model=self.model, input=texts_list)
        return [item.embedding for item in response.data]


def build_embedding_provider(fake: bool = False) -> EmbeddingProvider:
    if fake or SETTINGS.openai_api_key is None:
        return FakeEmbeddingProvider()
    return OpenAIEmbeddingProvider()
