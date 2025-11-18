"""Thin wrapper around ChromaDB to align with the PRD."""

from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import chromadb
from chromadb.api.types import EmbeddingFunction, Embeddings

from .config import SETTINGS

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .documents import DocumentChunk


class IdentityEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: list[str]) -> Embeddings:  # pragma: no cover - Chroma hook
        raise RuntimeError("Embeddings must be provided manually via upsert")


def _client() -> chromadb.PersistentClient:
    SETTINGS.chroma_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=SETTINGS.chroma_path_str)


def get_collection() -> chromadb.Collection:
    client = _client()
    return client.get_or_create_collection(
        name=SETTINGS.chroma_collection,
        embedding_function=IdentityEmbeddingFunction(),
        metadata={"hnsw:space": "cosine"},
    )


@dataclass(slots=True)
class SearchResult:
    id: str
    text: str
    score: float
    metadata: dict


def upsert_chunks(chunks: Iterable[DocumentChunk], embeddings: list[list[float]]) -> None:
    collection = get_collection()
    ids: list[str] = []
    metadatas: list[dict] = []
    documents: list[str] = []
    for chunk, _vector in zip(chunks, embeddings, strict=False):
        ids.append(chunk.id)
        meta = chunk.chroma_metadata()
        if isinstance(meta.get("tags"), list):
            meta["tags"] = ",".join(meta["tags"])
        metadatas.append(meta)
        documents.append(chunk.text)
    collection.upsert(ids=ids, metadatas=metadatas, documents=documents, embeddings=embeddings)


def delete_document(document_id: str) -> None:
    collection = get_collection()
    collection.delete(where={"document_id": document_id})


def query(
    query_text: str,
    top_k: int = 8,
    min_score: float = 0.0,
    collections: list[str] | None = None,
    embedding_provider=None,
) -> list[SearchResult]:
    provider = embedding_provider
    if provider is None:
        raise RuntimeError("embedding_provider is required for querying")
    vector = provider.embed([query_text])[0]
    where = None
    if collections:
        where = {"collection": {"$in": collections}}
    collection = get_collection()
    results = collection.query(
        query_embeddings=[vector],
        n_results=top_k,
        where=where,
    )
    hits: list[SearchResult] = []
    ids = results.get("ids", [[]])[0]
    documents = results.get("documents", [[]])[0]
    metadatas = results.get("metadatas", [[]])[0]
    distances = results.get("distances", [[]])[0]
    for chunk_id, chunk_text, metadata, distance in zip(
        ids, documents, metadatas, distances, strict=False
    ):
        score = 1 - float(distance)
        if score < min_score:
            continue
        if isinstance(metadata.get("tags"), str):
            metadata["tags"] = [t.strip() for t in metadata["tags"].split(",") if t.strip()]
        hits.append(
            SearchResult(
                id=chunk_id,
                text=chunk_text,
                score=score,
                metadata=metadata,
            )
        )
    return hits
