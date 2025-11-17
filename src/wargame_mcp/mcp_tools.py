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
from .instrumentation import correlation_scope, logger, track_latency
from .vectorstore import SearchResult, get_collection, normalize_metadata, query


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
    correlation_id: str | None = None,
) -> ToolResult:
    """Run a semantic search over the stored chunks."""

    with correlation_scope(correlation_id) as cid:
        provider = build_embedding_provider(fake=fake_embeddings)
        collection_filters = list(collections) if collections else None
        with track_latency(
            "search_wargame_docs",
            tool_name="search_wargame_docs",
            query=query_text,
            top_k=top_k,
            collections=collection_filters,
        ):
            hits = query(
                query_text=query_text,
                top_k=top_k,
                min_score=min_score,
                collections=collection_filters,
                embedding_provider=provider,
            )
        serialized = [_serialize_search_hit(hit) for hit in hits]
        logger.info(
            "tool_call.complete",
            tool_name="search_wargame_docs",
            result_count=len(serialized),
            correlation_id=cid,
        )
        return ToolResult(results=serialized)


def get_document_span(
    *,
    document_id: str,
    center_chunk_index: int,
    span: int = 2,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Return neighbouring chunks around a given hit."""

    if span < 0:
        raise ValueError("span must be >= 0")

    with correlation_scope(correlation_id) as cid:
        with track_latency(
            "get_doc_span",
            tool_name="get_doc_span",
            document_id=document_id,
            center_chunk_index=center_chunk_index,
            span=span,
        ):
            collection = get_collection()
            raw = collection.get(
                where={"document_id": document_id},
                include=["documents", "metadatas"],
            )
            chunks = []
            documents = _flatten(raw.get("documents", []))
            metadatas = _flatten(raw.get("metadatas", []))

            for text, metadata in zip(documents, metadatas):
                chunk_index = metadata.get("chunk_index")
                if chunk_index is None:
                    continue
                chunks.append(
                    {
                        "id": metadata.get("chunk_id"),
                        "chunk_index": int(chunk_index),
                        "text": text,
                        "metadata": normalize_metadata(metadata),
                    }
                )

            if not chunks:
                logger.info(
                    "tool_call.complete",
                    tool_name="get_doc_span",
                    result_count=0,
                    correlation_id=cid,
                )
                return {"chunks": []}

            chunks.sort(key=lambda item: item["chunk_index"])
            start = max(0, center_chunk_index - span)
            end = center_chunk_index + span

            window = [chunk for chunk in chunks if start <= chunk["chunk_index"] <= end]
        logger.info(
            "tool_call.complete",
            tool_name="get_doc_span",
            result_count=len(window),
            correlation_id=cid,
        )
        return {"chunks": window}


def list_collections_summary(*, correlation_id: str | None = None) -> dict[str, Any]:
    """Aggregate metadata counts per collection."""

    with correlation_scope(correlation_id) as cid:
        with track_latency("list_collections", tool_name="list_collections"):
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
        logger.info(
            "tool_call.complete",
            tool_name="list_collections",
            result_count=len(summaries),
            correlation_id=cid,
        )
        return {"collections": summaries}


def health_check_status(*, correlation_id: str | None = None) -> dict[str, Any]:
    """Return collection statistics for readiness checks."""

    with correlation_scope(correlation_id) as cid:
        with track_latency("health_check", tool_name="health_check"):
            collection = get_collection()
            count = collection.count()
        payload = {"status": "ok", "details": f"{count} chunks indexed"}
        logger.info(
            "tool_call.complete",
            tool_name="health_check",
            correlation_id=cid,
            chunks=count,
        )
        return payload


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
