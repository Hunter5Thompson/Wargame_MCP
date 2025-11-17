"""Shared document dataclasses used across the tooling."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Iterable


def _default_tags() -> list[str]:
    return []


@dataclass(slots=True)
class DocumentMetadata:
    document_id: str
    source_path: Path
    collection: str = "other"
    title: str | None = None
    year: int | None = None
    doctrine: str | None = None
    tags: list[str] = field(default_factory=_default_tags)

    def as_dict(self) -> dict:
        return {
            "document_id": self.document_id,
            "source": str(self.source_path),
            "collection": self.collection,
            "title": self.title,
            "year": self.year,
            "doctrine": self.doctrine,
            "tags": self.tags,
        }

    def chroma_dict(self) -> dict:
        data = self.as_dict()
        data["tags"] = ",".join(self.tags)
        return data


@dataclass(slots=True)
class DocumentChunk:
    id: str
    text: str
    metadata: DocumentMetadata
    chunk_index: int
    chunk_count: int

    def chroma_metadata(self) -> dict:
        base = self.metadata.chroma_dict()
        base.update({
            "chunk_index": self.chunk_index,
            "chunk_count": self.chunk_count,
            "chunk_id": self.id,
        })
        return base


@dataclass(slots=True)
class IngestionSummary:
    document_count: int
    chunk_count: int
    token_count: int
    started_at: datetime
    finished_at: datetime

    def as_dict(self) -> dict:
        return {
            "document_count": self.document_count,
            "chunk_count": self.chunk_count,
            "token_count": self.token_count,
            "started_at": self.started_at.isoformat(),
            "finished_at": self.finished_at.isoformat(),
        }


def ensure_year(value: int | None) -> int | None:
    if value is None:
        return None
    if 1900 <= value <= 2100:
        return value
    return None


def slugify(text: str) -> str:
    safe = [c.lower() if c.isalnum() else "-" for c in text]
    slug = "".join(safe).strip("-")
    return "-".join(filter(None, slug.split("-")))


def build_document_id(path: Path, title: str | None = None) -> str:
    if title:
        return f"{slugify(title)}-{abs(hash(path)) % (10**8)}"
    return f"doc-{abs(hash(path)) % (10**12)}"


def merge_tags(*tag_sets: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    merged: list[str] = []
    for tag_set in tag_sets:
        for tag in tag_set:
            tag_norm = tag.strip()
            if not tag_norm or tag_norm in seen:
                continue
            seen.add(tag_norm)
            merged.append(tag_norm)
    return merged
