"""MCP server exposing the Mem0 tools over stdio."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

from .memory_tools import (
    memory_add_entry,
    memory_delete_entry,
    memory_list_entries,
    memory_search_entries,
)

try:  # pragma: no cover - optional dependency
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover
    FastMCP = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover
    from mcp.server.fastmcp import FastMCP as FastMCPType


SERVER_NAME = "mem0-mcp"


def create_server() -> "FastMCPType":
    if FastMCP is None:  # pragma: no cover - depends on optional dependency
        raise RuntimeError(
            "The `mcp` package is required to run the MCP server. Install it with 'pip install mcp'."
        )

    server = FastMCP(SERVER_NAME)

    @server.tool()
    async def memory_search(
        query: str,
        user_id: str,
        limit: int | None = None,
        scopes: Iterable[str] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        return memory_search_entries(
            query=query,
            user_id=user_id,
            limit=limit,
            scopes=scopes,
            correlation_id=correlation_id,
        )

    @server.tool()
    async def memory_add(
        user_id: str,
        memory: str,
        scope: str | None = None,
        tags: Iterable[str] | None = None,
        source: str | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        return memory_add_entry(
            user_id=user_id,
            memory=memory,
            scope=scope,
            tags=tags,
            source=source,
            correlation_id=correlation_id,
        )

    @server.tool()
    async def memory_delete(memory_id: str, correlation_id: str | None = None) -> dict[str, Any]:
        return memory_delete_entry(memory_id=memory_id, correlation_id=correlation_id)

    @server.tool()
    async def memory_list(
        user_id: str,
        limit: int | None = None,
        scope: str | None = None,
        tags: Iterable[str] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        return memory_list_entries(
            user_id=user_id,
            limit=limit,
            scope=scope,
            tags=tags,
            correlation_id=correlation_id,
        )

    return server


def run() -> None:  # pragma: no cover
    create_server().run()


if __name__ == "__main__":  # pragma: no cover
    run()
