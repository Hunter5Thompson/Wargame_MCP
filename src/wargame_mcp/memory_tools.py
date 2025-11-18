"""Shared helpers for the Mem0-backed MCP tools."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from .config import SETTINGS
from .instrumentation import correlation_scope, logger, track_latency
from .mem0_client import get_mem0_client

if TYPE_CHECKING:
    from collections.abc import Iterable

DEFAULT_SCOPES = ["user", "scenario", "agent"]


def memory_search_entries(
    *,
    query: str,
    user_id: str,
    limit: int | None = None,
    scopes: Iterable[str] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Proxy the memory_search MCP tool."""

    if limit is None:
        limit = SETTINGS.mem0_default_limit
    if limit < 1:
        raise ValueError("limit must be >= 1")

    scope_filters = list(scopes) if scopes else DEFAULT_SCOPES

    with correlation_scope(correlation_id) as cid:
        with track_latency(
            "memory_search",
            tool_name="memory_search",
            user_id=user_id,
            limit=limit,
            scopes=scope_filters,
        ):
            client = get_mem0_client()
            results = client.memory_search(
                query=query,
                user_id=user_id,
                limit=limit,
                scopes=scope_filters,
            )
        logger.info(
            "tool_call.complete",
            tool_name="memory_search",
            correlation_id=cid,
            result_count=len(results),
        )
        return {"results": results}


def memory_add_entry(
    *,
    user_id: str,
    memory: str,
    scope: str | None = None,
    tags: Iterable[str] | None = None,
    source: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Proxy the memory_add MCP tool."""

    scope_value = scope or SETTINGS.mem0_default_scope

    with correlation_scope(correlation_id) as cid:
        with track_latency(
            "memory_add", tool_name="memory_add", user_id=user_id, scope=scope_value
        ):
            client = get_mem0_client()
            payload = client.memory_add(
                user_id=user_id,
                memory=memory,
                scope=scope_value,
                tags=tags,
                source=source,
            )
        logger.info(
            "tool_call.complete",
            tool_name="memory_add",
            correlation_id=cid,
            memory_id=payload.get("memory_id"),
        )
        return payload


def memory_delete_entry(
    *,
    memory_id: str,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Proxy the memory_delete MCP tool."""

    with correlation_scope(correlation_id) as cid:
        with track_latency("memory_delete", tool_name="memory_delete", memory_id=memory_id):
            client = get_mem0_client()
            payload = client.memory_delete(memory_id=memory_id)
        logger.info(
            "tool_call.complete",
            tool_name="memory_delete",
            correlation_id=cid,
            status=payload.get("status"),
        )
        return payload


def memory_list_entries(
    *,
    user_id: str,
    limit: int | None = None,
    scope: str | None = None,
    tags: Iterable[str] | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Proxy the memory_list MCP tool."""

    if limit is None:
        limit = SETTINGS.mem0_default_limit
    if limit < 1:
        raise ValueError("limit must be >= 1")

    with correlation_scope(correlation_id) as cid:
        with track_latency(
            "memory_list",
            tool_name="memory_list",
            user_id=user_id,
            scope=scope,
            limit=limit,
        ):
            client = get_mem0_client()
            results = client.memory_list(user_id=user_id, limit=limit, scope=scope, tags=tags)
        logger.info(
            "tool_call.complete",
            tool_name="memory_list",
            correlation_id=cid,
            result_count=len(results),
        )
        return {"results": results}
