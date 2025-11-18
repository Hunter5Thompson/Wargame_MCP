"""Simple unit tests that work without external dependencies."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

import pytest

from wargame_mcp.documents import (
    MAX_VALID_YEAR,
    MIN_VALID_YEAR,
    DocumentChunk,
    DocumentMetadata,
    IngestionSummary,
    ensure_year,
    slugify,
)
from wargame_mcp.embeddings import FakeEmbeddingProvider, build_embedding_provider
from wargame_mcp.mcp_tools import _flatten, _serialize_search_hit
from wargame_mcp.vectorstore import SearchResult


# Document tests
def test_document_metadata_creation():
    """Test creating DocumentMetadata."""
    metadata = DocumentMetadata(
        document_id="doc-123",
        source_path=Path("/tmp/test.md"),
        collection="test",
    )
    assert metadata.document_id == "doc-123"
    assert metadata.collection == "test"


def test_document_chunk_chroma_metadata():
    """Test DocumentChunk.chroma_metadata()."""
    metadata = DocumentMetadata(
        document_id="doc-1",
        source_path=Path("/test.md"),
        collection="test",
    )
    chunk = DocumentChunk(
        id="chunk-1",
        text="Test",
        metadata=metadata,
        chunk_index=2,
        chunk_count=10,
    )
    chroma_meta = chunk.chroma_metadata()
    assert chroma_meta["document_id"] == "doc-1"
    assert chroma_meta["chunk_index"] == 2
    assert chroma_meta["chunk_count"] == 10


def test_ingestion_summary_as_dict():
    """Test IngestionSummary.as_dict()."""
    start = datetime(2024, 1, 1, 12, 0, 0, tzinfo=UTC)
    end = datetime(2024, 1, 1, 12, 5, 0, tzinfo=UTC)
    summary = IngestionSummary(
        document_count=3,
        chunk_count=30,
        token_count=5000,
        started_at=start,
        finished_at=end,
    )
    result = summary.as_dict()
    assert result["document_count"] == 3
    assert result["chunk_count"] == 30
    assert result["token_count"] == 5000


def test_ensure_year_valid():
    """Test ensure_year with valid years."""
    assert ensure_year(2024) == 2024
    assert ensure_year(MIN_VALID_YEAR) == MIN_VALID_YEAR
    assert ensure_year(MAX_VALID_YEAR) == MAX_VALID_YEAR


def test_ensure_year_invalid():
    """Test ensure_year with invalid years."""
    assert ensure_year(1899) is None
    assert ensure_year(2101) is None
    assert ensure_year(None) is None


def test_slugify_basic():
    """Test slugify with basic text."""
    result = slugify("Hello World")
    assert "hello" in result.lower()
    assert "world" in result.lower()


# Embeddings tests
def test_fake_embedding_provider_basic():
    """Test FakeEmbeddingProvider generates embeddings."""
    provider = FakeEmbeddingProvider()
    embeddings = provider.embed(["test"])
    assert len(embeddings) == 1
    assert len(embeddings[0]) > 0


def test_fake_embedding_provider_deterministic():
    """Test that FakeEmbeddingProvider is deterministic."""
    provider = FakeEmbeddingProvider()
    emb1 = provider.embed(["test"])
    emb2 = provider.embed(["test"])
    assert emb1 == emb2


def test_fake_embedding_provider_empty_list():
    """Test FakeEmbeddingProvider with empty list."""
    provider = FakeEmbeddingProvider()
    embeddings = provider.embed([])
    assert embeddings == []


def test_build_embedding_provider_fake():
    """Test building fake embedding provider."""
    provider = build_embedding_provider(fake=True)
    assert isinstance(provider, FakeEmbeddingProvider)


# MCP tools tests
def test_flatten_simple_list():
    """Test _flatten with simple list."""
    assert _flatten([1, 2, 3]) == [1, 2, 3]


def test_flatten_nested_list():
    """Test _flatten with nested list."""
    assert _flatten([[1, 2], [3, 4]]) == [1, 2, 3, 4]


def test_flatten_empty_list():
    """Test _flatten with empty list."""
    assert _flatten([]) == []


def test_flatten_single_value():
    """Test _flatten with non-list value."""
    assert _flatten("single") == ["single"]


def test_serialize_search_hit_basic():
    """Test _serialize_search_hit with basic SearchResult."""
    hit = SearchResult(
        id="chunk-123",
        text="Test text",
        score=0.95,
        metadata={"collection": "test"},
    )
    result = _serialize_search_hit(hit)
    assert result["id"] == "chunk-123"
    assert result["text"] == "Test text"
    assert result["score"] == 0.95


def test_serialize_search_hit_preserves_metadata():
    """Test that _serialize_search_hit preserves metadata."""
    hit = SearchResult(
        id="chunk-1",
        text="Text",
        score=0.9,
        metadata={
            "collection": "nato",
            "document_id": "doc-1",
            "title": "Test",
        },
    )
    result = _serialize_search_hit(hit)
    assert result["metadata"]["title"] == "Test"
    assert result["metadata"]["collection"] == "nato"


# Vectorstore tests
def test_search_result_creation():
    """Test SearchResult dataclass."""
    result = SearchResult(
        id="chunk-123",
        text="Test chunk text",
        score=0.95,
        metadata={"collection": "test"},
    )
    assert result.id == "chunk-123"
    assert result.text == "Test chunk text"
    assert result.score == 0.95


def test_search_result_with_empty_metadata():
    """Test SearchResult with empty metadata."""
    result = SearchResult(
        id="chunk-1",
        text="Text",
        score=0.8,
        metadata={},
    )
    assert result.metadata == {}
