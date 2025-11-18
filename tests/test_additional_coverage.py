"""Additional tests to increase coverage."""

from __future__ import annotations

from types import SimpleNamespace

import pytest

from wargame_mcp.agent import (
    AgentConfig,
    MCPServer,
    ParsedToolCall,
    build_agent_payload,
    build_tool_resources,
    create_openai_client,
    extract_response_text,
    parse_tool_call,
)
from wargame_mcp.chunking import iter_documents, read_text
from wargame_mcp.embeddings import OpenAIEmbeddingProvider
from wargame_mcp.mcp_tools import _flatten


# Agent tests
def test_mcp_server_with_defaults():
    """Test MCPServer with default values."""
    server = MCPServer(server_name="test", command="cmd")
    assert server.args == ()
    assert server.env is None


def test_agent_config_creation():
    """Test AgentConfig with custom values."""
    config = AgentConfig(model="gpt-4", temperature=0.5)
    assert config.model == "gpt-4"
    assert config.temperature == 0.5


def test_build_tool_resources_no_mem0():
    """Test build_tool_resources without mem0 server."""
    config = AgentConfig(mem0_server=None)
    resources = build_tool_resources(config)
    assert len(resources["mcp"]) == 1


def test_build_agent_payload_includes_metadata():
    """Test build_agent_payload includes metadata."""
    config = AgentConfig()
    payload = build_agent_payload(
        config=config,
        question="Test?",
        user_id="u123",
        correlation_id="c456",
    )
    assert payload["metadata"]["user_id"] == "u123"
    assert payload["metadata"]["correlation_id"] == "c456"


def test_parse_tool_call_with_parsed_input():
    """Test parse_tool_call with ParsedToolCall."""
    call = ParsedToolCall(
        id="1",
        server_name="srv",
        tool_name="tool",
        arguments={},
    )
    result = parse_tool_call(call)
    assert result is call


def test_parse_tool_call_with_dict_arguments():
    """Test parse_tool_call with dict arguments."""
    raw = {
        "id": "123",
        "tool_name": "search",
        "arguments": {"query": "test"},
    }
    result = parse_tool_call(raw)
    assert result.arguments == {"query": "test"}


def test_parse_tool_call_with_json_string():
    """Test parse_tool_call with JSON string arguments."""
    raw = {
        "tool_name": "test",
        "arguments": '{"key": "value"}',
    }
    result = parse_tool_call(raw)
    assert result.arguments == {"key": "value"}


def test_parse_tool_call_with_invalid_json():
    """Test parse_tool_call with invalid JSON string."""
    raw = {
        "tool_name": "test",
        "arguments": "not json",
    }
    result = parse_tool_call(raw)
    assert result.arguments == {"raw": "not json"}


def test_parse_tool_call_with_non_dict_args():
    """Test parse_tool_call with non-dict arguments."""
    raw = {
        "tool_name": "test",
        "arguments": ["list"],
    }
    result = parse_tool_call(raw)
    assert result.arguments == {}


def test_parse_tool_call_missing_name_raises():
    """Test parse_tool_call raises when tool_name is missing."""
    raw = {"id": "123"}
    with pytest.raises(ValueError, match="Unable to determine tool name"):
        parse_tool_call(raw)


def test_parse_tool_call_uses_defaults():
    """Test parse_tool_call uses default values."""
    raw = {"tool_name": "test"}
    result = parse_tool_call(raw)
    assert result.id == "tool-call"
    assert result.server_name == "wargame-rag-mcp"


def test_extract_response_text_with_output_text_attr():
    """Test extract_response_text with output_text."""
    response = SimpleNamespace(output_text="  Response  ")
    result = extract_response_text(response)
    assert result == "Response"


def test_extract_response_text_with_dict_in_output():
    """Test extract_response_text with dict content."""
    response = SimpleNamespace(
        output_text="",
        output=[
            SimpleNamespace(
                content=[{"text": "Test response"}]
            )
        ],
    )
    result = extract_response_text(response)
    assert result == "Test response"


def test_extract_response_text_with_type_output_text():
    """Test extract_response_text with type output_text."""
    response = SimpleNamespace(
        output_text="",
        output=[
            SimpleNamespace(
                content=[
                    {"type": "output_text", "output": "Typed"}
                ]
            )
        ],
    )
    result = extract_response_text(response)
    assert result == "Typed"


def test_extract_response_text_empty():
    """Test extract_response_text with empty response returns empty string."""
    response = SimpleNamespace(output_text="", output=[])
    result = extract_response_text(response)
    assert result == ""


# Chunking tests
def test_iter_documents_empty_dir(tmp_path):
    """Test iter_documents with empty directory."""
    docs = list(iter_documents(tmp_path))
    assert docs == []


def test_iter_documents_finds_md_files(tmp_path):
    """Test iter_documents finds markdown files."""
    (tmp_path / "doc.md").write_text("# Test")
    docs = list(iter_documents(tmp_path))
    assert len(docs) >= 1


def test_read_text_reads_file(tmp_path):
    """Test read_text reads file content."""
    test_file = tmp_path / "test.md"
    test_file.write_text("content", encoding="utf-8")
    result = read_text(test_file)
    assert result == "content"


def test_read_text_file_not_found():
    """Test read_text raises FileNotFoundError."""
    from pathlib import Path

    with pytest.raises(FileNotFoundError):
        read_text(Path("/nonexistent.md"))


# Embeddings tests
def test_openai_provider_initialization():
    """Test OpenAIEmbeddingProvider initialization."""
    provider = OpenAIEmbeddingProvider(
        model="text-embedding-3-small",
        api_key="test-key",
    )
    assert provider.model == "text-embedding-3-small"


def test_openai_provider_requires_api_key():
    """Test OpenAIEmbeddingProvider requires API key or env var."""
    from wargame_mcp import config

    # Save original
    original = config.SETTINGS.openai_api_key

    # Test without API key
    config.SETTINGS.openai_api_key = None

    with pytest.raises(RuntimeError, match="OPENAI_API_KEY"):
        OpenAIEmbeddingProvider()

    # Restore
    config.SETTINGS.openai_api_key = original


# MCP tools additional coverage
def test_flatten_deeply_nested():
    """Test _flatten with deeply nested structure."""
    result = _flatten([[[1]]])
    # _flatten only flattens one level
    assert result == [[1]]


def test_flatten_mixed_nested():
    """Test _flatten with mixed types."""
    result = _flatten([["a"], ["b", "c"]])
    assert result == ["a", "b", "c"]


# Additional simple tests
def test_parsed_tool_call_attributes():
    """Test ParsedToolCall stores all attributes."""
    call = ParsedToolCall(
        id="test-id",
        server_name="test-server",
        tool_name="test-tool",
        arguments={"arg": "value"},
    )
    assert call.id == "test-id"
    assert call.server_name == "test-server"
    assert call.tool_name == "test-tool"
    assert call.arguments == {"arg": "value"}
