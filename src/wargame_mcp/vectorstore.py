"""Thin wrapper around ChromaDB to align with the PRD."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

try:  # pragma: no cover - optional dependency
    import chromadb
    from chromadb.api.types import EmbeddingFunction, Embeddings
except Exception:  # pragma: no cover - fallback implementation
    chromadb = None  # type: ignore

    class EmbeddingFunction:  # type: ignore
        pass

    Embeddings = list[list[float]]

from .config import SETTINGS
from .documents import DocumentChunk


class IdentityEmbeddingFunction(EmbeddingFunction):
    def __call__(self, input: list[str]) -> Embeddings:  # pragma: no cover - Chroma hook
        raise RuntimeError("Embeddings must be provided manually via upsert")


_FALLBACK_CLIENTS: dict[str, "_InMemoryClient"] = {}


def _client():
    SETTINGS.chroma_path.mkdir(parents=True, exist_ok=True)
    if chromadb is None:
        key = f"{SETTINGS.chroma_path_str}:{SETTINGS.chroma_collection}"
        if key not in _FALLBACK_CLIENTS:
            _FALLBACK_CLIENTS[key] = _InMemoryClient()
        return _FALLBACK_CLIENTS[key]
    return chromadb.PersistentClient(path=SETTINGS.chroma_path_str)


def get_collection():
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
    for chunk, vector in zip(chunks, embeddings):
        ids.append(chunk.id)
        metadatas.append(chunk.chroma_metadata())
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
    for chunk_id, chunk_text, metadata, distance in zip(ids, documents, metadatas, distances):
        score = 1 - float(distance)
        if score < min_score:
            continue
        hits.append(
            SearchResult(
                id=chunk_id,
                text=chunk_text,
                score=score,
                metadata=metadata,
            )
        )
    return hits


class _InMemoryClient:  # pragma: no cover - fallback
    def __init__(self) -> None:
        self.collections: dict[str, _InMemoryCollection] = {}

    def get_or_create_collection(self, name: str, **_kwargs):
        if name not in self.collections:
            self.collections[name] = _InMemoryCollection()
        return self.collections[name]


class _InMemoryCollection:  # pragma: no cover - fallback
    def __init__(self) -> None:
        self.records: dict[str, dict] = {}

    def upsert(self, ids: list[str], metadatas: list[dict], documents: list[str], embeddings: Embeddings) -> None:
        for chunk_id, metadata, text, embedding in zip(ids, metadatas, documents, embeddings):
            self.records[chunk_id] = {
                "metadata": metadata,
                "text": text,
                "embedding": embedding,
            }

    def delete(self, where: dict | None = None) -> None:
        if not where:
            self.records.clear()
            return
        to_delete = [
            chunk_id
            for chunk_id, record in self.records.items()
            if _matches_where(record["metadata"], where)
        ]
        for chunk_id in to_delete:
            self.records.pop(chunk_id, None)

    def query(self, query_embeddings: Embeddings, n_results: int, where: dict | None = None) -> dict:
        vector = query_embeddings[0]
        candidates = [
            (chunk_id, record)
            for chunk_id, record in self.records.items()
            if _matches_where(record["metadata"], where)
        ]
        scored = [
            (1 - _cosine_distance(vector, record["embedding"]), chunk_id, record)
            for chunk_id, record in candidates
        ]
        scored.sort(key=lambda item: item[0], reverse=True)
        top = scored[:n_results]
        return {
            "ids": [[chunk_id for _, chunk_id, _ in top]],
            "documents": [[record["text"] for _, _, record in top]],
            "metadatas": [[record["metadata"] for _, _, record in top]],
            "distances": [[1 - score for score, _, _ in top]],
        }

    def get(self, where: dict | None = None, include: list[str] | None = None) -> dict:
        matches = [
            (chunk_id, record)
            for chunk_id, record in self.records.items()
            if _matches_where(record["metadata"], where)
        ]
        include = include or ["ids", "documents", "metadatas"]
        response: dict[str, list] = {}
        if "ids" in include:
            response["ids"] = [chunk_id for chunk_id, _ in matches]
        if "documents" in include:
            response["documents"] = [record["text"] for _, record in matches]
        if "metadatas" in include:
            response["metadatas"] = [record["metadata"] for _, record in matches]
        return response

    def count(self) -> int:
        return len(self.records)


def _matches_where(metadata: dict, where: dict | None) -> bool:
    if not where:
        return True
    for key, value in where.items():
        if isinstance(value, dict) and "$in" in value:
            if metadata.get(key) not in value["$in"]:
                return False
        else:
            if metadata.get(key) != value:
                return False
    return True


def _cosine_distance(vec_a: list[float], vec_b: list[float]) -> float:
    if not vec_a or not vec_b:
        return 1.0
    dot = sum(a * b for a, b in zip(vec_a, vec_b))
    norm_a = sum(a * a for a in vec_a) ** 0.5
    norm_b = sum(b * b for b in vec_b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 1.0
    cosine = dot / (norm_a * norm_b)
    return 1 - cosine
