"""Simple tests to boost coverage without complex dependencies."""

from __future__ import annotations

from pathlib import Path

from wargame_mcp.config import SETTINGS
from wargame_mcp.documents import slugify
from wargame_mcp.embeddings import FakeEmbeddingProvider
from wargame_mcp.ingest import ingest_directory
from wargame_mcp.mcp_tools import ToolResult
from wargame_mcp.metadata_loader import metadata_for_document


# Settings tests
def test_settings_attributes():
    """Test SETTINGS has expected attributes."""
    assert hasattr(SETTINGS, "chroma_path")
    assert hasattr(SETTINGS, "chroma_collection")


# ToolResult tests
def test_tool_result_as_dict():
    """Test ToolResult.as_dict()."""
    result = ToolResult(results=[{"id": "1"}])
    assert result.as_dict() == {"results": [{"id": "1"}]}


# Metadata tests
def test_metadata_for_document_simple(tmp_path):
    """Test metadata_for_document with simple file."""
    doc = tmp_path / "test.md"
    doc.write_text("# Test")
    metadata = metadata_for_document(doc)
    assert metadata.source_path == doc


# Slugify tests
def test_slugify_converts_to_lowercase():
    """Test slugify converts to lowercase."""
    result = slugify("UPPERCASE")
    assert result.islower()


# Embeddings tests
def test_fake_embedding_unicode_support():
    """Test FakeEmbeddingProvider handles Unicode."""
    provider = FakeEmbeddingProvider()
    result = provider.embed(["Test 你好"])
    assert len(result) == 1


# Ingest tests
def test_ingest_empty_directory(tmp_path):
    """Test ingest_directory with empty directory."""
    summary = ingest_directory(tmp_path, fake_embeddings=True)
    assert summary.document_count == 0
