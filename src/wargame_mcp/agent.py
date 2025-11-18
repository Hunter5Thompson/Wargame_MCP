"""Utilities for wiring the OpenAI Responses API to the MCP servers."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from importlib import import_module
from typing import Any, Callable, Protocol

from .mcp_tools import (
    get_document_span,
    health_check_status,
    list_collections_summary,
    search_wargame_documents,
)
from .memory_tools import (
    memory_add_entry,
    memory_delete_entry,
    memory_list_entries,
    memory_search_entries,
)

SYSTEM_PROMPT = """You are the WargameAssistantAgent, a doctrine-focused analyst.
Always follow this doctrine:
- Search the wargaming corpus via the wargame-rag-mcp server before stating facts.
- Query mem0-mcp memories whenever the user references past scenarios, decisions, or preferences.
- Merge findings from doctrine (RAG) and memory, mention concrete chunk titles, and highlight conflicts.
- If a tool is unavailable, explain the limitation in the final answer instead of hallucinating facts.
- Prefer concise COA tables, explicit assumptions, and cite lessons learned when recommending actions.
"""


@dataclass(slots=True)
class MCPServer:
    """Configuration for a single MCP server exposed to the agent."""

    server_name: str
    command: str
    args: tuple[str, ...] = ()
    env: dict[str, str] | None = None


@dataclass(slots=True)
class AgentConfig:
    """Runtime knobs for the OpenAI agent orchestration."""

    model: str = "gpt-4.1-mini"
    temperature: float = 0.3
    rag_server: MCPServer = field(
        default_factory=lambda: MCPServer(server_name="wargame-rag-mcp", command="wargame-rag-mcp")
    )
    mem0_server: MCPServer | None = field(
        default_factory=lambda: MCPServer(server_name="wargame-mem0-mcp", command="wargame-mem0-mcp")
    )


class ResponsesAPI(Protocol):
    def create(self, **kwargs: Any) -> Any:  # pragma: no cover - protocol definition
        ...


class OpenAIClient(Protocol):
    responses: ResponsesAPI  # pragma: no cover - protocol definition


def create_openai_client(**kwargs: Any) -> OpenAIClient:
    """Instantiate the OpenAI SDK client (importing lazily to keep optional)."""

    client_class = getattr(import_module("openai"), "OpenAI")
    return client_class(**kwargs)


@dataclass(slots=True)
class ParsedToolCall:
    """Normalized representation of an OpenAI tool call payload."""

    id: str
    server_name: str
    tool_name: str
    arguments: dict[str, Any]


ToolExecutor = Callable[[ParsedToolCall], str]


class WargameAssistantAgent:
    """Bridges the OpenAI Responses API with the MCP servers."""

    def __init__(self, *, client: OpenAIClient, config: AgentConfig | None = None) -> None:
        self.client = client
        self.config = config or AgentConfig()

    def run_conversation(
        self,
        *,
        question: str,
        user_id: str,
        correlation_id: str | None = None,
        tool_executor: ToolExecutor | None = None,
    ) -> str:
        """Send the user question to OpenAI and resolve any tool calls."""

        payload = build_agent_payload(
            config=self.config,
            question=question,
            user_id=user_id,
            correlation_id=correlation_id,
        )
        response = self.client.responses.create(**payload)

        while getattr(response, "status", None) == "requires_action":
            if tool_executor is None:
                raise RuntimeError(
                    "OpenAI requested manual tool outputs but no executor was provided."
                    " Ensure the MCP integration is available or supply a ToolExecutor."
                )

            required = getattr(response, "required_action", None)
            submit_block = getattr(required, "submit_tool_outputs", None)
            tool_calls = getattr(submit_block, "tool_calls", None) or []
            outputs = []
            for raw_call in tool_calls:
                parsed = parse_tool_call(raw_call)
                outputs.append({"tool_call_id": parsed.id, "output": tool_executor(parsed)})
            response = self.client.responses.create(response_id=response.id, tool_outputs=outputs)

        if getattr(response, "status", None) not in {"completed", "finished", None}:
            raise RuntimeError(f"Unexpected response status: {getattr(response, 'status', None)}")

        return extract_response_text(response)

def build_agent_payload(
    *, config: AgentConfig, question: str, user_id: str, correlation_id: str | None = None
) -> dict[str, Any]:
    """Helper used by the CLI and tests to inspect the outbound request."""

    tool_resources = build_tool_resources(config)
    metadata = {"user_id": user_id}
    if correlation_id:
        metadata["correlation_id"] = correlation_id

    return {
        "model": config.model,
        "temperature": config.temperature,
        "input": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": question},
        ],
        "metadata": metadata,
        "tool_resources": tool_resources,
    }


def build_tool_resources(config: AgentConfig) -> dict[str, list[dict[str, Any]]]:
    """Serialize MCP server definitions for the Responses API."""

    servers = [config.rag_server]
    if config.mem0_server is not None:
        servers.append(config.mem0_server)

    return {
        "mcp": [
            {
                "type": "stdio",
                "server_name": server.server_name,
                "command": server.command,
                "args": list(server.args),
                "env": server.env or {},
            }
            for server in servers
        ]
    }


def parse_tool_call(raw_call: Any) -> ParsedToolCall:
    """Handle tool call payloads from real or fake OpenAI responses."""

    if isinstance(raw_call, ParsedToolCall):
        return raw_call

    def _lookup(value: Any, name: str) -> Any:
        if value is None:
            return None
        if isinstance(value, dict):
            return value.get(name)
        return getattr(value, name, None)

    call_id = _lookup(raw_call, "id") or "tool-call"
    server_name = (
        _lookup(raw_call, "server_name")
        or _lookup(raw_call, "serverName")
        or _lookup(_lookup(raw_call, "mcp"), "server_name")
        or "wargame-rag-mcp"
    )
    tool_name = (
        _lookup(raw_call, "tool_name")
        or _lookup(raw_call, "name")
        or _lookup(_lookup(raw_call, "function"), "name")
    )
    arguments = (
        _lookup(raw_call, "arguments")
        or _lookup(_lookup(raw_call, "function"), "arguments")
        or {}
    )
    if isinstance(arguments, str):
        try:
            arguments = json.loads(arguments)
        except json.JSONDecodeError:
            arguments = {"raw": arguments}
    if not isinstance(arguments, dict):
        arguments = {}

    if tool_name is None:
        raise ValueError("Unable to determine tool name from OpenAI payload.")

    return ParsedToolCall(
        id=str(call_id),
        server_name=str(server_name),
        tool_name=str(tool_name),
        arguments=arguments,
    )


def extract_response_text(response: Any) -> str:
    """Best-effort extraction that works with the Responses SDK and our fakes."""

    output_text = getattr(response, "output_text", None)
    if isinstance(output_text, str) and output_text.strip():
        return output_text.strip()

    output = getattr(response, "output", None) or []
    for block in output:
        contents = getattr(block, "content", None) or []
        for content in contents:
            text = getattr(content, "text", None) or content.get("text") if isinstance(content, dict) else None
            if text:
                return text.strip()
            if isinstance(content, dict) and content.get("type") == "output_text":
                candidate = content.get("output", "")
                if candidate:
                    return str(candidate).strip()
    if hasattr(response, "content") and isinstance(response.content, list):
        for item in response.content:
            text = item.get("text") if isinstance(item, dict) else getattr(item, "text", None)
            if text:
                return text.strip()
    return ""


class LocalToolExecutor:
    """Executes tool calls directly against the in-process helpers (for tests/demo)."""

    def __init__(self, *, fake_embeddings: bool = False) -> None:
        self.fake_embeddings = fake_embeddings
        self.history: list[ParsedToolCall] = []

    def __call__(self, call: ParsedToolCall) -> str:
        self.history.append(call)
        if call.server_name == "wargame-rag-mcp":
            return self._run_rag_tool(call)
        if call.server_name == "wargame-mem0-mcp":
            return self._run_memory_tool(call)
        raise ValueError(f"Unsupported MCP server: {call.server_name}")

    def _run_rag_tool(self, call: ParsedToolCall) -> str:
        name = call.tool_name
        args = call.arguments
        if name == "search_wargame_docs":
            try:
                top_k = int(args.get("top_k", 8))
                min_score = float(args.get("min_score", 0.0))
            except (ValueError, TypeError) as exc:
                return json.dumps({"error": f"Invalid parameter type: {exc}"})
            result = search_wargame_documents(
                query_text=args.get("query") or args.get("query_text", ""),
                top_k=top_k,
                min_score=min_score,
                collections=args.get("collections"),
                fake_embeddings=self.fake_embeddings,
            )
            return json.dumps(result.as_dict())
        if name == "get_doc_span":
            try:
                center_chunk_index = int(args.get("center_chunk_index", 0))
                span = int(args.get("span", 2))
            except (ValueError, TypeError) as exc:
                return json.dumps({"error": f"Invalid parameter type: {exc}"})
            payload = get_document_span(
                document_id=args["document_id"],
                center_chunk_index=center_chunk_index,
                span=span,
            )
            return json.dumps(payload)
        if name == "list_collections":
            return json.dumps(list_collections_summary())
        if name == "health_check":
            return json.dumps(health_check_status())
        raise ValueError(f"Unsupported RAG tool: {name}")

    def _run_memory_tool(self, call: ParsedToolCall) -> str:
        name = call.tool_name
        args = call.arguments
        if name == "memory_search":
            try:
                limit = int(args.get("limit", 5))
            except (ValueError, TypeError) as exc:
                return json.dumps({"error": f"Invalid parameter type: {exc}"})
            payload = memory_search_entries(
                query=args.get("query", ""),
                user_id=args["user_id"],
                limit=limit,
                scopes=args.get("scopes"),
            )
            return json.dumps(payload)
        if name == "memory_add":
            payload = memory_add_entry(
                user_id=args["user_id"],
                memory=args["memory"],
                scope=args.get("scope"),
                tags=args.get("tags"),
                source=args.get("source"),
            )
            return json.dumps(payload)
        if name == "memory_delete":
            payload = memory_delete_entry(memory_id=args["memory_id"])
            return json.dumps(payload)
        if name == "memory_list":
            try:
                limit = int(args.get("limit", 5))
            except (ValueError, TypeError) as exc:
                return json.dumps({"error": f"Invalid parameter type: {exc}"})
            payload = memory_list_entries(
                user_id=args["user_id"],
                limit=limit,
                scope=args.get("scope"),
                tags=args.get("tags"),
            )
            return json.dumps(payload)
        raise ValueError(f"Unsupported memory tool: {name}")
