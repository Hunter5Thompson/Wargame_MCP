"""Typer CLI entrypoint exposing the MCP-style workflows."""

from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from ._rich_compat import Console, Table
from .ingest import ingest_directory
from .mcp_tools import (
    health_check_status,
    list_collections_summary,
    search_wargame_documents,
)
from .vectorstore import get_collection

app = typer.Typer(help="Utilities for the Wargame Knowledge & Memory System prototype.")
console = Console()


@app.command()
def ingest(
    input_dir: Path = typer.Argument(..., exists=True, file_okay=False, dir_okay=True, readable=True),
    fake_embeddings: bool = typer.Option(False, help="Use deterministic fake embeddings."),
):
    """Ingest all supported documents from INPUT_DIR into Chroma."""
    ingest_directory(input_dir, fake_embeddings=fake_embeddings)


@app.command("search")
def search_cmd(
    query_text: str = typer.Argument(..., help="Semantic search query."),
    top_k: int = typer.Option(8, min=1, max=50),
    min_score: float = typer.Option(0.0, min=0.0, max=1.0),
    collections: Optional[str] = typer.Option(None, help="Comma separated list of collection filters."),
    fake_embeddings: bool = typer.Option(False, help="Use deterministic embeddings for offline testing."),
):
    """Search previously ingested documents."""
    collections_list = collections.split(",") if collections else None
    result = search_wargame_documents(
        query_text=query_text,
        top_k=top_k,
        min_score=min_score,
        collections=collections_list,
        fake_embeddings=fake_embeddings,
    )
    if not result.results:
        console.print("No results found.")
        raise typer.Exit(code=0)

    table = Table(title="search_wargame_docs")
    table.add_column("Chunk ID")
    table.add_column("Score", justify="right")
    table.add_column("Collection")
    table.add_column("Snippet")
    for hit in result.results:
        snippet = hit["text"][:120].replace("\n", " ") + ("…" if len(hit["text"]) > 120 else "")
        table.add_row(
            hit["id"],
            f"{hit['score']:.3f}",
            str(hit["metadata"].get("collection")),
            snippet,
        )
    console.print(table)


@app.command("list-collections")
def list_collections() -> None:
    """List available collections and document counts."""
    summary = list_collections_summary()
    table = Table(title="Collections")
    table.add_column("Name")
    table.add_column("Chunks", justify="right")
    for collection in summary["collections"]:
        table.add_row(collection["name"], str(collection["document_count"]))
    console.print(table)


@app.command("health-check")
def health_check() -> None:
    """Ensure we can reach the Chroma store."""
    console.print(health_check_status())
