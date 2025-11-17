from __future__ import annotations

from wargame_mcp.memory_tools import (
    memory_add_entry,
    memory_delete_entry,
    memory_list_entries,
    memory_search_entries,
)


def test_memory_flow(fake_mem0_client):
    add_result = memory_add_entry(user_id="user-123", memory="Prefers low collateral", scope="user")
    assert add_result["status"] == "created"

    search = memory_search_entries(query="collateral", user_id="user-123", limit=5)
    assert search["results"], "memory_search should return results"

    listing = memory_list_entries(user_id="user-123", limit=10)
    assert len(listing["results"]) == 1

    memory_id = listing["results"][0]["memory_id"]
    delete = memory_delete_entry(memory_id=memory_id)
    assert delete["status"] == "deleted"
