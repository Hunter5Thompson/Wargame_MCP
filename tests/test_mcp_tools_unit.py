"""Unit tests for mcp_tools module."""

from __future__ import annotations

import pytest

from wargame_mcp.mcp_tools import _flatten, _serialize_search_hit
from wargame_mcp.vectorstore import SearchResult


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


def test_flatten_mixed_nested():
    """Test _flatten with mixed nested structure."""
    result = _flatten([[1, 2], [3], [4, 5, 6]])
    assert result == [1, 2, 3, 4, 5, 6]


def test_flatten_deeply_nested():
    """Test _flatten with deeply nested lists (only flattens one level)."""
    result = _flatten([[[1, 2]], [[3, 4]]])
    assert result == [[1, 2], [3, 4]]


def test_flatten_single_nested_list():
    """Test _flatten with single nested list."""
    assert _flatten([[1, 2, 3]]) == [1, 2, 3]


def test_flatten_none_value():
    """Test _flatten with None."""
    assert _flatten(None) == [None]


def test_flatten_mixed_types():
    """Test _flatten with mixed types in nested lists."""
    result = _flatten([["a", "b"], [1, 2], [True, False]])
    assert result == ["a", "b", 1, 2, True, False]


def test_serialize_search_hit_basic():
    """Test _serialize_search_hit with basic SearchResult."""
    hit = SearchResult(
        id="chunk-123",
        text="Test text",
        score=0.95,
        metadata={"collection": "test", "document_id": "doc-1"},
    )

    result = _serialize_search_hit(hit)

    assert result["id"] == "chunk-123"
    assert result["text"] == "Test text"
    assert result["score"] == 0.95
    assert result["metadata"]["collection"] == "test"
    assert result["metadata"]["document_id"] == "doc-1"


def test_serialize_search_hit_with_chunk_metadata():
    """Test _serialize_search_hit with chunk_index and chunk_count."""
    hit = SearchResult(
        id="chunk-5",
        text="Chunk text",
        score=0.88,
        metadata={
            "document_id": "doc-1",
            "chunk_index": 5,
            "chunk_count": 10,
        },
    )

    result = _serialize_search_hit(hit)

    assert result["metadata"]["chunk_index"] == 5
    assert result["metadata"]["chunk_count"] == 10


def test_serialize_search_hit_preserves_all_metadata():
    """Test that _serialize_search_hit preserves all metadata fields."""
    hit = SearchResult(
        id="chunk-1",
        text="Text",
        score=0.9,
        metadata={
            "collection": "nato",
            "document_id": "doc-1",
            "title": "Test",
            "year": 2024,
            "tags": ["tag1", "tag2"],
            "custom_field": "custom_value",
        },
    )

    result = _serialize_search_hit(hit)

    assert result["metadata"]["title"] == "Test"
    assert result["metadata"]["year"] == 2024
    assert result["metadata"]["tags"] == ["tag1", "tag2"]
    assert result["metadata"]["custom_field"] == "custom_value"


def test_serialize_search_hit_creates_dict_copy():
    """Test that _serialize_search_hit creates a copy of metadata."""
    metadata = {"collection": "test", "document_id": "doc-1"}
    hit = SearchResult(id="chunk-1", text="Text", score=0.9, metadata=metadata)

    result = _serialize_search_hit(hit)

    # Modify the result metadata
    result["metadata"]["new_field"] = "new_value"

    # Original metadata should not be affected
    assert "new_field" not in metadata


def test_serialize_search_hit_with_empty_metadata():
    """Test _serialize_search_hit with empty metadata."""
    hit = SearchResult(
        id="chunk-1",
        text="Text",
        score=0.85,
        metadata={},
    )

    result = _serialize_search_hit(hit)

    assert result["metadata"] == {}


def test_serialize_search_hit_with_special_characters():
    """Test _serialize_search_hit with special characters in text."""
    hit = SearchResult(
        id="chunk-1",
        text="Text with\nnewlines\tand\ttabs",
        score=0.9,
        metadata={"collection": "test"},
    )

    result = _serialize_search_hit(hit)

    assert "\n" in result["text"]
    assert "\t" in result["text"]


def test_serialize_search_hit_with_unicode():
    """Test _serialize_search_hit with Unicode text."""
    hit = SearchResult(
        id="chunk-1",
        text="Unicode: 你好世界 🌍",
        score=0.92,
        metadata={"collection": "test"},
    )

    result = _serialize_search_hit(hit)

    assert "你好世界" in result["text"]
    assert "🌍" in result["text"]


def test_serialize_search_hit_score_precision():
    """Test that _serialize_search_hit preserves score precision."""
    hit = SearchResult(
        id="chunk-1",
        text="Text",
        score=0.123456789,
        metadata={},
    )

    result = _serialize_search_hit(hit)

    assert result["score"] == 0.123456789
