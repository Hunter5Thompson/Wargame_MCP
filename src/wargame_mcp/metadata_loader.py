"""Helpers that derive metadata from neighbour files and naming conventions."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import yaml

from .documents import DocumentMetadata, build_document_id, ensure_year, merge_tags

if TYPE_CHECKING:
    from pathlib import Path

COLLECTIONS = {"doctrine", "aar", "scenario", "intel", "other"}


def _load_yaml(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
        return data or {}
    except yaml.YAMLError:
        return None


def metadata_for_document(doc_path: Path) -> DocumentMetadata:
    yaml_path = doc_path.with_suffix(doc_path.suffix + ".meta.yml")
    yaml_data = _load_yaml(yaml_path)

    title = yaml_data.get("title") if yaml_data else doc_path.stem.replace("_", " ")
    document_id = yaml_data.get("document_id") if yaml_data else None
    if not document_id:
        document_id = build_document_id(doc_path, title=title)

    collection = (yaml_data or {}).get("collection", "other")
    if collection not in COLLECTIONS:
        collection = "other"

    year = ensure_year((yaml_data or {}).get("year"))
    doctrine = (yaml_data or {}).get("doctrine")
    tags = merge_tags((yaml_data or {}).get("tags", []))

    return DocumentMetadata(
        document_id=document_id,
        source_path=doc_path,
        collection=collection,
        title=title,
        year=year,
        doctrine=doctrine,
        tags=tags,
    )
