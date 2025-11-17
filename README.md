# Wargame MCP

Dieses Repository liefert nicht nur die Product Requirements, sondern jetzt auch eine minimal lauffähige Referenzimplementierung für die in [docs/PRD.md](docs/PRD.md) beschriebenen Ziele:

* **Ingestion-Tooling:** Chunking nach Tiktoken-Heuristik (800 Tokens + 200 Overlap) und Ablage in einer lokalen Chroma-Collection.
* **RAG-Befehle:** CLI-Kommandos für `search_wargame_docs`, `list_collections` und `health_check` (analog zu den MCP-Tools).
* **Mem0-Integration:** MCP-Tools für `memory_search`, `memory_add`, `memory_delete` und `memory_list`, inklusive eigenem `mem0-mcp` Server.
* **Konfigurierbare Embeddings:** Wahlweise echte OpenAI Embeddings (über `OPENAI_API_KEY`) oder deterministische Fake-Vektoren für Offline-Tests.

## Quickstart

```bash
uv pip install -e .
export CHROMA_PATH="./data/chroma"
# Optional: export MEM0_BASE_URL="http://localhost:7777"
# Optional: export MEM0_API_KEY="test"
# Optional: export OPENAI_API_KEY="sk-..."
```

### Beispiel-Ingestion

```bash
wargame-mcp ingest examples/sample_docs --fake-embeddings
```

### Suche & Health-Check

```bash
wargame-mcp search "urban defense" --fake-embeddings
wargame-mcp list-collections
wargame-mcp health-check
```

### MCP-Server & Inspector-Test

Das optionale MCP-Server-Interface basiert auf `mcp.server.FastMCP`. Installiere
dafür zusätzlich das `mcp`-Paket und starte den Server via Script:

```bash
pip install mcp  # falls noch nicht vorhanden
wargame-rag-mcp
```

Für einen schnellen Integrationstest lässt sich der offizielle MCP Inspector
nutzen (im `mcp`-Paket enthalten). In einem zweiten Terminal prüfst du damit die
Tools:

```bash
python -m mcp.server.inspect --command wargame-rag-mcp
```

Der Inspector ruft `search_wargame_docs`, `get_doc_span`, `list_collections` und
`health_check` direkt über MCP auf.

### Mem0 MCP Server

Sobald eine Mem0-Instanz (self-hosted oder Cloud) verfügbar ist, lassen sich die
Memory-Tools per MCP bereitstellen:

```bash
export MEM0_BASE_URL="http://localhost:7777"  # oder Cloud-Endpunkt
export MEM0_API_KEY="test-key"
wargame-mem0-mcp
```

Die selben Tools lassen sich wieder mit dem Inspector testen:

```bash
python -m mcp.server.inspect --command wargame-mem0-mcp
```

Unterstützt werden `memory_search`, `memory_add`, `memory_delete` und
`memory_list`. Die Instrumentierung entspricht der RAG-Seite (JSON-Logs,
correlation_id, Latenzmetriken).

### OpenAI Agent-Integration

Die Referenz-Agentschicht befindet sich in `wargame_mcp.agent`. Damit lässt
sich der OpenAI Responses-Workflow samt MCP-Tools nutzen:

```bash
wargame-mcp agent-run "Bewerte COA Alpha gegen Bravo" \
  --user-id demo --model gpt-4.1-mini
```

Der Befehl erzeugt das komplette Payload inklusive `tool_resources` für
`wargame-rag-mcp` und `wargame-mem0-mcp`. Mit `--dry-run` wird dieses Payload nur
ausgegeben, sodass man es auch direkt gegen die OpenAI Responses API schicken
kann. Der System-Prompt ist wortgleich zu Abschnitt 6.2/6.3 im PRD, wodurch jede
Agent-Antwort die dort beschriebenen Tool-Nutzungsregeln befolgt.

### Tests

```bash
pytest
```

## Logging & Debugging

* Alle Tool-Aufrufe laufen über `structlog`-JSON-Events. Eine optionale
  `correlation_id` kann bei jedem MCP-Call mitgegeben werden und wird automatisch
  bis in den Vectorstore durchgereicht.
* Die Laufzeiten für CLI- und MCP-Operationen landen im In-Memory-Metrikpuffer
  (`wargame_mcp.instrumentation.latencies`). Über `latencies.summary()` lässt sich
  ein aktueller Überblick über `count`, `avg_ms`, `max_ms` und Fehlerraten
  anzeigen.

Alle weiterführenden Anforderungen, Datenmodelle und Betriebsrichtlinien stehen weiterhin im [PRD](docs/PRD.md).
