"""Final push to 70% coverage."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from wargame_mcp.chunking import iter_documents, read_text
from wargame_mcp.mcp_tools import get_document_span, health_check_status, list_collections_summary


# Chunking additional coverage
def test_iter_documents_recursive_structure(tmp_path):
    """Test iter_documents finds files in subdirectories."""
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "doc.md").write_text("# Test")

    docs = list(iter_documents(tmp_path))
    assert len(docs) >= 1


def test_read_text_utf8_encoding(tmp_path):
    """Test read_text with UTF-8."""
    file = tmp_path / "test.md"
    file.write_text("UTF-8: 你好", encoding="utf-8")
    content = read_text(file)
    assert "你好" in content


# MCP tools additional coverage
@patch("wargame_mcp.mcp_tools.get_collection")
def test_health_check_status_returns_ok(mock_get_collection):
    """Test health_check_status returns ok status."""
    mock_collection = MagicMock()
    mock_collection.count.return_value = 100
    mock_get_collection.return_value = mock_collection

    result = health_check_status()

    assert result["status"] == "ok"
    assert "100" in result["details"]


@patch("wargame_mcp.mcp_tools.get_collection")
def test_list_collections_summary_empty(mock_get_collection):
    """Test list_collections_summary with empty collection."""
    mock_collection = MagicMock()
    mock_collection.get.return_value = {"metadatas": []}
    mock_get_collection.return_value = mock_collection

    result = list_collections_summary()

    assert "collections" in result
    assert isinstance(result["collections"], list)


@patch("wargame_mcp.mcp_tools.get_collection")
def test_get_document_span_empty_collection(mock_get_collection):
    """Test get_document_span with no matching chunks."""
    mock_collection = MagicMock()
    mock_collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}
    mock_get_collection.return_value = mock_collection

    result = get_document_span(document_id="nonexistent", center_chunk_index=0)

    assert result["chunks"] == []


@patch("wargame_mcp.mcp_tools.get_collection")
def test_get_document_span_invalid_span_raises(mock_get_collection):
    """Test get_document_span with negative span."""
    with pytest.raises(ValueError, match="span must be >= 0"):
        get_document_span(document_id="test", center_chunk_index=0, span=-1)


# Additional agent coverage
from wargame_mcp.agent import MCPServer, build_tool_resources, AgentConfig


def test_mcp_server_with_env():
    """Test MCPServer with environment variables."""
    server = MCPServer(
        server_name="test",
        command="cmd",
        env={"KEY": "value"},
    )
    assert server.env == {"KEY": "value"}


def test_build_tool_resources_includes_all_fields():
    """Test build_tool_resources includes all server fields."""
    config = AgentConfig(
        rag_server=MCPServer(
            server_name="rag",
            command="rag-cmd",
            args=("arg1",),
            env={"VAR": "val"},
        ),
        mem0_server=None,
    )

    resources = build_tool_resources(config)

    server = resources["mcp"][0]
    assert server["type"] == "stdio"
    assert server["server_name"] == "rag"
    assert server["command"] == "rag-cmd"
    assert server["args"] == ["arg1"]
    assert server["env"] == {"VAR": "val"}


# More documents coverage
from wargame_mcp.documents import ensure_year, DocumentMetadata, DocumentChunk


def test_ensure_year_edge_cases():
    """Test ensure_year with edge case values."""
    from wargame_mcp.documents import MIN_VALID_YEAR, MAX_VALID_YEAR

    assert ensure_year(MIN_VALID_YEAR) == MIN_VALID_YEAR
    assert ensure_year(MAX_VALID_YEAR) == MAX_VALID_YEAR
    assert ensure_year(MIN_VALID_YEAR - 1) is None
    assert ensure_year(MAX_VALID_YEAR + 1) is None


def test_document_metadata_defaults_mutable():
    """Test that default lists don't leak between instances."""
    meta1 = DocumentMetadata(document_id="1", source_path=Path("/tmp/1.md"))
    meta2 = DocumentMetadata(document_id="2", source_path=Path("/tmp/2.md"))

    meta1.tags.append("tag1")

    assert "tag1" in meta1.tags
    assert "tag1" not in meta2.tags


def test_document_chunk_metadata_includes_all_fields():
    """Test that chroma_metadata includes all required fields."""
    metadata = DocumentMetadata(
        document_id="doc-1",
        source_path=Path("/test.md"),
        collection="test",
        title="Test Title",
        year=2024,
    )
    chunk = DocumentChunk(
        id="chunk-1",
        text="Text",
        metadata=metadata,
        chunk_index=5,
        chunk_count=10,
    )

    chroma_meta = chunk.chroma_metadata()

    assert chroma_meta["document_id"] == "doc-1"
    assert chroma_meta["collection"] == "test"
    assert chroma_meta["title"] == "Test Title"
    assert chroma_meta["year"] == 2024
    assert chroma_meta["chunk_index"] == 5
    assert chroma_meta["chunk_count"] == 10
