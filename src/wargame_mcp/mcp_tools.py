"""Shared business logic for the MCP tools.

The Typer CLI as well as the MCP server import the helpers in this module so
that both entrypoints produce identical JSON payloads.  Keeping the logic in a
single place also makes it straightforward to exercise the code from tests
without having to spin up an MCP runtime.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Iterable

from .embeddings import build_embedding_provider
from .vectorstore import SearchResult, get_collection, query


@dataclass(slots=True)
class ToolResult:
    """Typed representation of the search output used by CLI/MCP."""

    results: list[dict[str, Any]]

    def as_dict(self) -> dict[str, Any]:
        return {"results": self.results}


def search_wargame_documents(
    *,
    query_text: str,
    top_k: int = 8,
    min_score: float = 0.0,
    collections: Iterable[str] | None = None,
    fake_embeddings: bool = False,
) -> ToolResult:
    """Run a semantic search over the stored chunks."""

    provider = build_embedding_provider(fake=fake_embeddings)
    hits = query(
        query_text=query_text,
        top_k=top_k,
        min_score=min_score,
        collections=list(collections) if collections else None,
        embedding_provider=provider,
    )
    serialized = [_serialize_search_hit(hit) for hit in hits]
    return ToolResult(results=serialized)


def get_document_span(
    *,
    document_id: str,
    center_chunk_index: int,
    span: int = 2,
) -> dict[str, Any]:
    """Return neighbouring chunks around a given hit."""

    if span < 0:
        raise ValueError("span must be >= 0")

    collection = get_collection()
    raw = collection.get(
        where={"document_id": document_id},
        include=["ids", "documents", "metadatas"],
    )
    chunks = []
    ids = _flatten(raw.get("ids", []))
    documents = _flatten(raw.get("documents", []))
    metadatas = _flatten(raw.get("metadatas", []))

    for chunk_id, text, metadata in zip(ids, documents, metadatas):
        chunk_index = metadata.get("chunk_index")
        if chunk_index is None:
            continue
        chunks.append(
            {
                "id": chunk_id,
                "chunk_index": int(chunk_index),
                "text": text,
                "metadata": metadata,
            }
        )

    if not chunks:
        return {"chunks": []}

    chunks.sort(key=lambda item: item["chunk_index"])
    start = max(0, center_chunk_index - span)
    end = center_chunk_index + span

    window = [chunk for chunk in chunks if start <= chunk["chunk_index"] <= end]
    return {"chunks": window}


def list_collections_summary() -> dict[str, Any]:
    """Aggregate metadata counts per collection."""

    collection = get_collection()
    agg: dict[str, set[str]] = {}
    result = collection.get(include=["metadatas"])
    for metadata in _flatten(result.get("metadatas", [])):
        name = metadata.get("collection", "other")
        doc_id = metadata.get("document_id")
        if doc_id is None:
            continue
        agg.setdefault(name, set()).add(doc_id)

    summaries = [
        {"name": name, "document_count": len(doc_ids), "description": ""}
        for name, doc_ids in sorted(agg.items())
    ]
    return {"collections": summaries}


def health_check_status() -> dict[str, Any]:
    """Return collection statistics for readiness checks."""

    collection = get_collection()
    count = collection.count()
    return {"status": "ok", "details": f"{count} chunks indexed"}


def _serialize_search_hit(hit: SearchResult) -> dict[str, Any]:
    metadata = dict(hit.metadata)
    metadata.setdefault("chunk_index", metadata.get("chunk_index"))
    metadata.setdefault("chunk_count", metadata.get("chunk_count"))
    return {
        "id": hit.id,
        "text": hit.text,
        "score": hit.score,
        "metadata": metadata,
    }


def _flatten(value: Any) -> list[Any]:
    if not isinstance(value, list):
        return [value]
    if not value:
        return []
    if isinstance(value[0], list):
        flattened: list[Any] = []
        for item in value:
            flattened.extend(item if isinstance(item, list) else [item])
        return flattened
    return value
