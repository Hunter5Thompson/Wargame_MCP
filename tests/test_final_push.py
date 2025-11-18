"""Final tests to exceed 70% coverage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from wargame_mcp.embeddings import FakeEmbeddingProvider
from wargame_mcp.vectorstore import SearchResult


# Embeddings coverage boost
def test_fake_embedding_provider_multiple_texts():
    """Test FakeEmbeddingProvider with multiple texts."""
    provider = FakeEmbeddingProvider()
    texts = ["text1", "text2", "text3"]

    embeddings = provider.embed(texts)

    assert len(embeddings) == 3
    assert all(len(emb) > 0 for emb in embeddings)
    # Different texts should produce different embeddings
    assert embeddings[0] != embeddings[1]


def test_fake_embedding_provider_long_text():
    """Test FakeEmbeddingProvider with very long text."""
    provider = FakeEmbeddingProvider()
    long_text = "word " * 1000

    embeddings = provider.embed([long_text])

    assert len(embeddings) == 1
    assert len(embeddings[0]) > 0


def test_fake_embedding_provider_special_chars():
    """Test FakeEmbeddingProvider with special characters."""
    provider = FakeEmbeddingProvider()
    texts = ["test\n\nlines", "tabs\t\there", "special!@#$%"]

    embeddings = provider.embed(texts)

    assert len(embeddings) == 3


# Vectorstore coverage boost
def test_search_result_with_metadata_variations():
    """Test SearchResult with various metadata combinations."""
    result1 = SearchResult(
        id="1",
        text="Text",
        score=0.9,
        metadata={"collection": "test"},
    )
    result2 = SearchResult(
        id="2",
        text="Text",
        score=0.8,
        metadata={
            "collection": "test",
            "document_id": "doc-1",
            "chunk_index": 0,
            "chunk_count": 5,
            "title": "Title",
            "year": 2024,
        },
    )

    assert result1.metadata["collection"] == "test"
    assert result2.metadata["chunk_index"] == 0
    assert result2.metadata["year"] == 2024


def test_search_result_score_precision():
    """Test SearchResult maintains score precision."""
    result = SearchResult(
        id="1",
        text="Text",
        score=0.987654321,
        metadata={},
    )

    assert result.score == 0.987654321


# Additional chunking coverage
from wargame_mcp.chunking import iter_documents


def test_iter_documents_ignores_hidden_files(tmp_path):
    """Test iter_documents doesn't return hidden files."""
    (tmp_path / "visible.md").write_text("# Visible")
    (tmp_path / ".hidden.md").write_text("# Hidden")

    docs = list(iter_documents(tmp_path))

    paths = [d.name for d in docs]
    assert ".hidden.md" not in paths
    assert "visible.md" in paths


def test_iter_documents_only_markdown(tmp_path):
    """Test iter_documents only returns .md files."""
    (tmp_path / "doc.md").write_text("# MD")
    (tmp_path / "doc.txt").write_text("Text")
    (tmp_path / "doc.py").write_text("# Python")

    docs = list(iter_documents(tmp_path))

    assert all(d.suffix == ".md" for d in docs)
    assert len(docs) == 1


# Additional agent coverage
from wargame_mcp.agent import ParsedToolCall, parse_tool_call


def test_parse_tool_call_with_server_name_field():
    """Test parse_tool_call extracts server_name from various locations."""
    # Test with direct server_name
    call1 = {"tool_name": "test", "server_name": "direct"}
    result1 = parse_tool_call(call1)
    assert result1.server_name == "direct"

    # Test with serverName (camelCase)
    call2 = {"tool_name": "test", "serverName": "camel"}
    result2 = parse_tool_call(call2)
    assert result2.server_name == "camel"


def test_parse_tool_call_with_function_object():
    """Test parse_tool_call with nested function object."""
    from types import SimpleNamespace

    call = SimpleNamespace(
        id="123",
        function=SimpleNamespace(
            name="tool_name",
            arguments='{"key": "value"}',
        ),
    )

    result = parse_tool_call(call)

    assert result.tool_name == "tool_name"
    assert result.arguments == {"key": "value"}


# Additional documents coverage
from wargame_mcp.documents import IngestionSummary
from datetime import UTC, datetime


def test_ingestion_summary_dict_format():
    """Test IngestionSummary.as_dict() format."""
    start = datetime(2024, 1, 1, 10, 0, 0, tzinfo=UTC)
    end = datetime(2024, 1, 1, 10, 5, 0, tzinfo=UTC)

    summary = IngestionSummary(
        document_count=5,
        chunk_count=50,
        token_count=10000,
        started_at=start,
        finished_at=end,
    )

    result = summary.as_dict()

    assert isinstance(result["started_at"], str)
    assert isinstance(result["finished_at"], str)
    assert "T" in result["started_at"]  # ISO format
