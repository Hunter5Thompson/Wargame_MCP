"""Document ingestion CLI."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from rich.console import Console
from rich.table import Table

from .chunking import chunk_text, iter_documents, read_text
from .config import SETTINGS
from .documents import DocumentChunk, IngestionSummary
from .embeddings import build_embedding_provider
from .metadata_loader import metadata_for_document
from .vectorstore import delete_document, upsert_chunks

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
    start = datetime.utcnow()
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

    end = datetime.utcnow()
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
