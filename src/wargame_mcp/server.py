"""MCP server exposing the wargame tools over stdio."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Iterable

from .mcp_tools import (
    get_document_span,
    health_check_status,
    list_collections_summary,
    search_wargame_documents,
)

try:  # pragma: no cover - optional runtime dependency
    from mcp.server.fastmcp import FastMCP
except Exception:  # pragma: no cover - optional runtime dependency
    FastMCP = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover - imported for typing only
    from mcp.server.fastmcp import FastMCP as FastMCPType


SERVER_NAME = "wargame-rag-mcp"


def create_server() -> "FastMCPType":
    """Instantiate the FastMCP server with tool bindings."""

    if FastMCP is None:  # pragma: no cover - depends on optional dependency
        raise RuntimeError(
            "The `mcp` package is required to run the MCP server. Install it with 'pip install mcp'."
        )

    server = FastMCP(SERVER_NAME)

    @server.tool()
    async def search_wargame_docs(
        query: str,
        top_k: int = 8,
        min_score: float = 0.0,
        collections: Iterable[str] | None = None,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Mirror of the search_wargame_docs MCP tool."""

        return search_wargame_documents(
            query_text=query,
            top_k=top_k,
            min_score=min_score,
            collections=collections,
            correlation_id=correlation_id,
        ).as_dict()

    @server.tool()
    async def get_doc_span(
        document_id: str,
        center_chunk_index: int,
        span: int = 2,
        correlation_id: str | None = None,
    ) -> dict[str, Any]:
        """Fetch the textual neighbourhood for a chunk."""

        return get_document_span(
            document_id=document_id,
            center_chunk_index=center_chunk_index,
            span=span,
            correlation_id=correlation_id,
        )

    @server.tool()
    async def list_collections(correlation_id: str | None = None) -> dict[str, Any]:
        """List every collection with aggregated counts."""

        return list_collections_summary(correlation_id=correlation_id)

    @server.tool()
    async def health_check(correlation_id: str | None = None) -> dict[str, Any]:
        """Ping the Chroma backend."""

        return health_check_status(correlation_id=correlation_id)

    return server


def run() -> None:  # pragma: no cover - thin wrapper
    """Run the MCP server."""

    create_server().run()


if __name__ == "__main__":  # pragma: no cover - manual invocation helper
    run()
