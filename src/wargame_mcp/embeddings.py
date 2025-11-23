"""Embedding provider abstractions."""

from __future__ import annotations

import hashlib

try:
    from openai import OpenAI
except Exception:  # pragma: no cover - optional dependency at runtime
    OpenAI = None  # type: ignore

from typing import TYPE_CHECKING

from .config import SETTINGS

if TYPE_CHECKING:
    from collections.abc import Iterable


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
    def __init__(
        self, model: str | None = None, api_key: str | None = None, base_url: str | None = None
    ) -> None:
        self.model = model or SETTINGS.embedding_model
        api_key = api_key or SETTINGS.openai_api_key
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is required for real embeddings")
        self._fallback = None
        if OpenAI is None:
            self._fallback = FakeEmbeddingProvider()
            self.client = None
        else:
            self.client = OpenAI(api_key=api_key, base_url=base_url or SETTINGS.openai_base_url)

    def embed(self, texts: Iterable[str]) -> list[list[float]]:
        texts_list = list(texts)
        if self._fallback is not None:
            return self._fallback.embed(texts_list)
        response = self.client.embeddings.create(model=self.model, input=texts_list)
        return [item.embedding for item in response.data]


def build_embedding_provider(fake: bool = False) -> EmbeddingProvider:
    if fake or SETTINGS.openai_api_key is None:
        return FakeEmbeddingProvider()
    return OpenAIEmbeddingProvider()
