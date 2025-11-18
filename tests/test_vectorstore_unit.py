"""Unit tests for vectorstore module."""

from __future__ import annotations

import pytest

from wargame_mcp.vectorstore import SearchResult


def test_search_result_creation():
    """Test SearchResult dataclass."""
    result = SearchResult(
        id="chunk-123",
        text="Test chunk text",
        score=0.95,
        metadata={"collection": "test", "document_id": "doc-1"},
    )

    assert result.id == "chunk-123"
    assert result.text == "Test chunk text"
    assert result.score == 0.95
    assert result.metadata["collection"] == "test"


def test_search_result_with_empty_metadata():
    """Test SearchResult with empty metadata."""
    result = SearchResult(
        id="chunk-1",
        text="Text",
        score=0.8,
        metadata={},
    )

    assert result.metadata == {}


def test_search_result_score_bounds():
    """Test SearchResult with various score values."""
    # Test valid scores
    for score in [0.0, 0.5, 0.99, 1.0]:
        result = SearchResult(id="test", text="text", score=score, metadata={})
        assert result.score == score


def test_search_result_with_complex_metadata():
    """Test SearchResult with complex metadata."""
    metadata = {
        "collection": "nato",
        "document_id": "doc-123",
        "title": "Urban Warfare",
        "year": 2024,
        "tags": ["doctrine", "urban"],
        "chunk_index": 5,
        "chunk_count": 20,
    }

    result = SearchResult(
        id="chunk-1",
        text="Complex metadata test",
        score=0.88,
        metadata=metadata,
    )

    assert result.metadata["year"] == 2024
    assert result.metadata["tags"] == ["doctrine", "urban"]
    assert result.metadata["chunk_index"] == 5
