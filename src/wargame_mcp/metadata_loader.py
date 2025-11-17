"""Helpers that derive metadata from neighbour files and naming conventions."""

from __future__ import annotations

from pathlib import Path
from typing import Any

try:  # pragma: no cover - optional dependency
    import yaml
except Exception:  # pragma: no cover - fallback parser
    yaml = None  # type: ignore

from .documents import DocumentMetadata, build_document_id, ensure_year, merge_tags

COLLECTIONS = {"doctrine", "aar", "scenario", "intel", "other"}


def _load_yaml(path: Path) -> dict[str, Any] | None:
    if not path.exists():
        return None
    text = path.read_text(encoding="utf-8")
    if yaml is None:
        return _parse_simple_yaml(text)
    try:
        data = yaml.safe_load(text)
        return data or {}
    except yaml.YAMLError:
        return _parse_simple_yaml(text)


def _parse_simple_yaml(text: str) -> dict[str, Any]:
    data: dict[str, Any] = {}
    current_list: str | None = None
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("- ") and current_list:
            data.setdefault(current_list, []).append(stripped[2:].strip())
            continue
        if ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if not value:
            current_list = key
            data.setdefault(key, [])
            continue
        current_list = None
        data[key] = _coerce_scalar(value)
    return data


def _coerce_scalar(value: str) -> Any:
    lowered = value.lower()
    if lowered in {"null", "none"}:
        return None
    if lowered in {"true", "false"}:
        return lowered == "true"
    try:
        return int(value)
    except ValueError:
        return value.strip("'\"")


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
