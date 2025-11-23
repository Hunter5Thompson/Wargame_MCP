"""Document ingestion CLI."""

from __future__ import annotations

import importlib.util
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from .chunking import chunk_text, iter_documents, read_text
from .config import SETTINGS
from .documents import DocumentChunk, IngestionSummary
from .embeddings import build_embedding_provider
from .metadata_loader import metadata_for_document
from .vectorstore import delete_document, upsert_chunks

if TYPE_CHECKING:
    from pathlib import Path

if importlib.util.find_spec("rich") is not None:
    from rich.console import Console  # pragma: no cover - optional dependency
    from rich.table import Table  # pragma: no cover - optional dependency

    console = Console()
else:  # pragma: no cover - fallback for environments without rich
    class Console:
        def log(self, message: str) -> None:  # pragma: no cover - simple logging
            print(message)

        def print(self, message: str = "") -> None:  # pragma: no cover
            if isinstance(message, Table):
                print(str(message))
            else:
                print(message)

    class Table:  # pragma: no cover - placeholder
        def __init__(self, *args, **kwargs):
            self.rows = []
            self.columns: list[str] = []

        def add_column(self, name: str, **_kwargs):
            self.columns.append(name)

        def add_row(self, *row):
            self.rows.append(row)

        def __str__(self) -> str:
            lines = [" | ".join(self.columns)] if self.columns else []
            for row in self.rows:
                lines.append(" | ".join(str(item) for item in row))
            return "\n".join(lines)

    console = Console()


def _ingest_file(path: Path, fake_embeddings: bool) -> tuple[list[DocumentChunk], int]:
    """Ingest a single file with comprehensive error handling."""
    try:
        metadata = metadata_for_document(path)
        text = read_text(path)
        result = chunk_text(metadata, text, SETTINGS.embedding_model)
        delete_document(metadata.document_id)
        provider = build_embedding_provider(fake=fake_embeddings)
        vectors = provider.embed([chunk.text for chunk in result.chunks])
        upsert_chunks(result.chunks, vectors)
        return result.chunks, result.token_count
    except FileNotFoundError as exc:
        console.log(f"[red]ERROR:[/red] File not found: {path}")
        raise RuntimeError(f"File not found: {path}") from exc
    except PermissionError as exc:
        console.log(f"[red]ERROR:[/red] Permission denied: {path}")
        raise RuntimeError(f"Permission denied: {path}") from exc
    except Exception as exc:
        console.log(f"[red]ERROR:[/red] Failed to ingest {path}: {exc}")
        raise RuntimeError(f"Failed to ingest {path}: {exc}") from exc


def ingest_directory(input_dir: Path, fake_embeddings: bool = False) -> IngestionSummary:
    """Ingest all documents from a directory with error handling and reporting."""
    start = datetime.now(UTC)
    document_count = 0
    chunk_count = 0
    token_count = 0
    failed_files: list[tuple[Path, str]] = []

    for file_path in iter_documents(input_dir):
        try:
            chunks, tokens = _ingest_file(file_path, fake_embeddings=fake_embeddings)
            document_count += 1
            chunk_count += len(chunks)
            token_count += tokens
            console.log(f"[green]✓[/green] Ingested {file_path} → {len(chunks)} chunks")
        except Exception as exc:
            failed_files.append((file_path, str(exc)))
            console.log(f"[red]✗[/red] Failed to ingest {file_path}: {exc}")

    end = datetime.now(UTC)
    summary = IngestionSummary(
        document_count=document_count,
        chunk_count=chunk_count,
        token_count=token_count,
        started_at=start,
        finished_at=end,
    )
    _print_summary(summary)

    if failed_files:
        console.print("\n[yellow]Failed files:[/yellow]")
        for path, error in failed_files:
            console.print(f"  • {path}: {error}")

    return summary


def _print_summary(summary: IngestionSummary) -> None:
    table = Table(title="Ingestion Summary")
    table.add_column("Metric")
    table.add_column("Value", justify="right")
    table.add_row("Documents", str(summary.document_count))
    table.add_row("Chunks", str(summary.chunk_count))
    table.add_row("Tokens", str(summary.token_count))
    table.add_row("Started", summary.started_at.isoformat())
    table.add_row("Finished", summary.finished_at.isoformat())
    console.print(table)
