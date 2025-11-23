"""Thin wrapper around ChromaDB to align with the PRD."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any

from .config import SETTINGS

if TYPE_CHECKING:
    from collections.abc import Iterable

    from .documents import DocumentChunk

if importlib.util.find_spec("chromadb") is not None:
    from chromadb.api.types import EmbeddingFunction, Embeddings  # pragma: no cover - optional
else:  # pragma: no cover - optional
    Embeddings = list[list[float]]
    EmbeddingFunction = Any


def _import_chromadb():
    chromadb_spec = importlib.util.find_spec("chromadb")
    if chromadb_spec is None:  # pragma: no cover - optional dependency
        raise ModuleNotFoundError(
            "chromadb is required for vectorstore operations; install chromadb>=0.5.0"
        )
    import chromadb

    return chromadb


def _use_fallback_store() -> bool:
    return importlib.util.find_spec("chromadb") is None


def _identity_embedding_function(chromadb_module: Any) -> Any:
    base = getattr(chromadb_module.api.types, "EmbeddingFunction", object)

    class IdentityEmbeddingFunction(base):  # type: ignore[misc]
        def __call__(self, input: list[str]) -> Embeddings:  # pragma: no cover - Chroma hook
            raise RuntimeError("Embeddings must be provided manually via upsert")

    return IdentityEmbeddingFunction()


def _client():
    chromadb = _import_chromadb()
    SETTINGS.chroma_path.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(path=SETTINGS.chroma_path_str)


def get_collection():
    if _use_fallback_store():
        return _FallbackCollection()
    client = _client()
    return client.get_or_create_collection(
        name=SETTINGS.chroma_collection,
        embedding_function=_identity_embedding_function(_import_chromadb()),
        metadata={"hnsw:space": "cosine"},
    )


_fallback_store: list[dict[str, Any]] = []


class _FallbackCollection:
    def get(self, where: dict | None = None, include: list[str] | None = None) -> dict[str, list]:
        include = include or []
        results = {"ids": [], "documents": [], "metadatas": []}
        for entry in _fallback_store:
            if where:
                doc_filter = where.get("document_id")
                if doc_filter is not None and entry["metadata"].get("document_id") != doc_filter:
                    continue
            results["ids"].append(entry["id"])
            if "documents" in include:
                results.setdefault("documents", []).append(entry["text"])
            if "metadatas" in include:
                results.setdefault("metadatas", []).append(entry["metadata"])
        results["ids"] = [results["ids"]]
        if "documents" in include:
            results["documents"] = [results["documents"]]
        if "metadatas" in include:
            results["metadatas"] = [results["metadatas"]]
        return results

    def count(self) -> int:
        return len(_fallback_store)


@dataclass(slots=True)
class SearchResult:
    id: str
    text: str
    score: float
    metadata: dict


def _cosine_similarity(vector_a: list[float], vector_b: list[float]) -> float:
    if not vector_a or not vector_b:
        return 0.0
    length = min(len(vector_a), len(vector_b))
    dot = sum(vector_a[i] * vector_b[i] for i in range(length))
    norm_a = sum(x * x for x in vector_a[:length]) ** 0.5
    norm_b = sum(x * x for x in vector_b[:length]) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    # Convert cosine distance to similarity score between 0-1
    cosine = dot / (norm_a * norm_b)
    return max(min((cosine + 1) / 2, 1.0), 0.0)


def upsert_chunks(chunks: Iterable[DocumentChunk], embeddings: list[list[float]]) -> None:
    if _use_fallback_store():
        _fallback_store.clear()
        for chunk, vector in zip(chunks, embeddings, strict=False):
            meta = chunk.chroma_metadata()
            if isinstance(meta.get("tags"), list):
                meta["tags"] = ",".join(meta["tags"])
            _fallback_store.append(
                {"id": chunk.id, "text": chunk.text, "metadata": meta, "embedding": vector}
            )
        return

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
    if _use_fallback_store():
        remaining = [entry for entry in _fallback_store if entry["metadata"].get("document_id") != document_id]
        _fallback_store[:] = remaining
        return
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
    if _use_fallback_store():
        hits: list[SearchResult] = []
        for entry in _fallback_store:
            if where:
                collection_filter = where.get("collection", {}).get("$in")
                if collection_filter and entry["metadata"].get("collection") not in collection_filter:
                    continue
            stored_vector = entry.get("embedding", [])
            score = _cosine_similarity(vector, stored_vector)
            if score < min_score:
                continue
            metadata = dict(entry["metadata"])
            if isinstance(metadata.get("tags"), str):
                metadata["tags"] = [t.strip() for t in metadata["tags"].split(",") if t.strip()]
            hits.append(
                SearchResult(
                    id=entry["id"],
                    text=entry["text"],
                    score=score,
                    metadata=metadata,
                )
            )
        hits.sort(key=lambda r: r.score, reverse=True)
        return hits[:top_k]

    collection = get_collection()
    results = collection.query(
        query_embeddings=[vector],
        n_results=top_k,
        where=where,
    )
    hits = _build_search_results(results, min_score)
    return hits


def _build_search_results(results: dict, min_score: float) -> list[SearchResult]:
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
