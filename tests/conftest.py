from __future__ import annotations

import sys
import uuid
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))


class FakeMem0Client:
    def __init__(self) -> None:
        self.memories: dict[str, dict[str, str]] = {}

    def memory_add(self, *, user_id: str, memory: str, scope: str, tags, source):
        memory_id = uuid.uuid4().hex
        entry = {
            "memory_id": memory_id,
            "memory": memory,
            "user_id": user_id,
            "scope": scope,
            "tags": list(tags or []),
            "source": source or "test",
            "score": 1.0,
        }
        self.memories[memory_id] = entry
        return {"memory_id": memory_id, "status": "created"}

    def memory_search(self, *, query: str, user_id: str, limit: int, scopes):
        lowered = query.lower()
        matches = [
            entry
            for entry in self.memories.values()
            if user_id == entry["user_id"] and lowered in entry["memory"].lower()
        ]
        for entry in matches:
            entry.setdefault("score", 0.95)
        return matches[:limit]

    def memory_delete(self, *, memory_id: str):
        if memory_id in self.memories:
            del self.memories[memory_id]
            return {"status": "deleted"}
        return {"status": "not_found"}

    def memory_list(self, *, user_id: str, limit: int, scope: str | None, tags):
        entries = [entry for entry in self.memories.values() if entry["user_id"] == user_id]
        if scope:
            entries = [entry for entry in entries if entry["scope"] == scope]
        return entries[:limit]


@pytest.fixture(autouse=True)
def fake_mem0_client():
    from wargame_mcp.mem0_client import set_mem0_client

    client = FakeMem0Client()
    set_mem0_client(client)  # type: ignore[arg-type]
    yield client
    set_mem0_client(None)
