from __future__ import annotations

import os
import uuid
from pathlib import Path

import pytest

from wargame_mcp import config
from wargame_mcp.ingest import ingest_directory
from wargame_mcp.mcp_tools import (
    get_document_span,
    health_check_status,
    list_collections_summary,
    search_wargame_documents,
)


def _configure_chroma(tmp_path):
    config.SETTINGS.chroma_path = tmp_path / "chroma"
    config.SETTINGS.chroma_collection = f"test_{uuid.uuid4().hex}"


@pytest.mark.skipif(
    os.getenv("CI") == "true" and not os.path.exists(os.path.expanduser("~/.cache/tiktoken")),
    reason="Tiktoken encoding download may fail in CI without cache",
)
def test_search_and_span(tmp_path):
    _configure_chroma(tmp_path)
    try:
        ingest_directory(Path("examples/sample_docs"), fake_embeddings=True)
    except Exception as e:
        if "403" in str(e) or "Forbidden" in str(e):
            pytest.skip(f"Tiktoken encoding download failed: {e}")
        raise

    result = search_wargame_documents(query_text="urban", fake_embeddings=True)
    assert result.results, "expected at least one hit"
    first = result.results[0]

    span = get_document_span(
        document_id=first["metadata"]["document_id"],
        center_chunk_index=first["metadata"].get("chunk_index", 0),
        span=1,
    )
    assert span["chunks"], "span should return neighbouring chunks"

    collections = list_collections_summary()
    assert collections["collections"], "expected aggregated collections"

    status = health_check_status()
    assert status["status"] == "ok"
