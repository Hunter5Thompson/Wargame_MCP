from __future__ import annotations

import json
import uuid
from pathlib import Path
from types import SimpleNamespace

from wargame_mcp import config
from wargame_mcp.agent import AgentConfig, LocalToolExecutor, WargameAssistantAgent
from wargame_mcp.ingest import ingest_directory
from wargame_mcp.memory_tools import memory_add_entry


class FakeToolCall:
    def __init__(
        self, *, call_id: str, server_name: str, tool_name: str, arguments: dict[str, object]
    ):
        self.id = call_id
        self.server_name = server_name
        self.tool_name = tool_name
        self.arguments = arguments


class FakeResponse:
    def __init__(
        self,
        *,
        response_id: str,
        status: str,
        tool_calls: list[FakeToolCall] | None = None,
        output_text: str = "",
    ):
        self.id = response_id
        self.status = status
        self.output_text = output_text
        if tool_calls:
            submit = SimpleNamespace(tool_calls=tool_calls)
            self.required_action = SimpleNamespace(submit_tool_outputs=submit)
        else:
            self.required_action = None


class FakeResponses:
    def __init__(self) -> None:
        self.invocations: list[dict[str, object]] = []
        self.tool_calls = [
            FakeToolCall(
                call_id="memory-call",
                server_name="wargame-mem0-mcp",
                tool_name="memory_search",
                arguments={"query": "Baltic Shield", "user_id": "demo-user", "limit": 3},
            ),
            FakeToolCall(
                call_id="rag-call",
                server_name="wargame-rag-mcp",
                tool_name="search_wargame_docs",
                arguments={"query": "urban defense", "top_k": 4, "min_score": 0.0},
            ),
        ]

    def create(self, **kwargs):  # pragma: no cover - exercised indirectly
        self.invocations.append(kwargs)
        if "response_id" not in kwargs:
            return FakeResponse(
                response_id="resp-1", status="requires_action", tool_calls=self.tool_calls
            )

        outputs = {
            item["tool_call_id"]: json.loads(item["output"])
            for item in kwargs.get("tool_outputs", [])
        }
        memory_summary = ""
        doc_summary = ""
        for call in self.tool_calls:
            payload = outputs.get(call.id, {})
            if call.tool_name == "memory_search":
                results = payload.get("results") or []
                if results:
                    memory_summary = results[0]["memory"]
            if call.tool_name == "search_wargame_docs":
                results = payload.get("results") or []
                if results:
                    doc_summary = results[0]["metadata"].get("title", "")
        final_text = f"Memories: {memory_summary}\nDoctrine: {doc_summary}"
        return FakeResponse(response_id="resp-2", status="completed", output_text=final_text)


class FakeOpenAIClient:
    def __init__(self) -> None:
        self.responses = FakeResponses()


def _configure_chroma(tmp_path: Path) -> None:
    config.SETTINGS.chroma_path = tmp_path / "chroma"
    config.SETTINGS.chroma_collection = f"agent_{uuid.uuid4().hex}"


def test_agent_flow_uses_tools(tmp_path, fake_mem0_client):
    _configure_chroma(tmp_path)
    ingest_directory(Path("examples/sample_docs"), fake_embeddings=True)
    memory_add_entry(
        user_id="demo-user", memory="Baltic Shield 2025 bevorzugte COA Bravo", scope="scenario"
    )

    fake_client = FakeOpenAIClient()
    agent = WargameAssistantAgent(client=fake_client, config=AgentConfig(model="fake-model"))
    executor = LocalToolExecutor(fake_embeddings=True)

    answer = agent.run_conversation(
        question="Welche Lessons Learned gelten für urbane Verteidigung?",
        user_id="demo-user",
        tool_executor=executor,
    )

    assert "Baltic Shield" in answer
    assert executor.history, "expected at least one tool call"
    tool_names = {call.tool_name for call in executor.history}
    assert {"memory_search", "search_wargame_docs"}.issubset(tool_names)
