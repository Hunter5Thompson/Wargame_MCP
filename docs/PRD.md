# Wargame Knowledge & Memory System (PRD)

## 1. Ziel & Kontext

Wir bauen ein System, mit dem Agenten (über OpenAI):

- auf Wargaming-Dokumente (Doktrin, Szenarien, AARs, Studien) via MCP-RAG-Server zugreifen können,
- über einen Memory-Layer (Mem0) langfristige Erfahrungen, Präferenzen und Episoden speichern und wieder abrufen können,
- und dadurch ohne menschliches Eingreifen möglichst viele Abfragen & Analyse-Aufgaben selbstständig lösen.

LLM-Provider in Produktion: ausschließlich OpenAI (Responses API / Agents SDK).

## 2. Scope

### 2.1 In-Scope

- **MCP-RAG-Server („wargame-rag-mcp“)**
  - Ingestion von Dokumenten (Batch-Job/CLI).
  - Semantische Suche + Filter auf Wargaming-Korpus.
  - Zugriff per MCP-Tools: `search_wargame_docs`, `get_doc_span`, `list_collections`, `health_check`.
- **Memory-Layer via Mem0 („mem0-mcp“)**
  - Speicherung von User-Präferenzen, Episoden und Agent-Heuristiken.
  - Zugriff per MCP-Tools: `memory_search`, `memory_add`, `memory_delete`, `memory_list`.
- **Agenten-Schicht („WargameAssistantAgent“)**
  - Implementiert mit OpenAI (Responses/Agents).
  - Nutzt MCP-Tools aus RAG & Memory.
  - Kann selbstständig Fragen analysieren, Dokumente abrufen, Memories nutzen und Antworten generieren.

### 2.2 Out-of-Scope (v1)

- Kein automatisches Schreiben/Überschreiben des Wargame-Korpus.
- Kein Deployment-Management externer Services.
- Kein Benutzer-Identity-Provider (User-IDs als String übergeben).

## 3. System-Overview & Architektur

### 3.1 Komponenten

1. **Wargame-RAG-MCP-Server**
   - Python-Service mit lokalem Dokumentenzugriff, Chroma Vector Store und MCP-Tools.
2. **Memory-MCP (Mem0)**
   - Mem0-Instanz mit MCP-Server, der die API kapselt.
3. **Agent-Orchestrierung (OpenAI)**
   - Agents mit System Prompt, Tool-Definitionen und Konfiguration.
4. **Client-Ebene**
   - CLI, UI, Chat-Frontend etc., die über OpenAI API mit Agents sprechen.

### 3.2 Datenfluss (High-Level)

1. Client sendet User-Query an OpenAI-Agent.
2. Agent ruft `memory_search` für Präferenzen/Erfahrungen auf.
3. Agent ruft `search_wargame_docs` für Doktrinen/Studien auf.
4. Agent kombiniert Informationen, optional erweitert mit `get_doc_span`.
5. Agent generiert Antwort und speichert neue Erkenntnisse über `memory_add`.

## 4. MCP-RAG-Server – „wargame-rag-mcp“

### 4.1 Tech-Stack

- Python 3.11, Dependency-Management via `uv`.
- MCP SDK: offizielles `mcp` Paket.
- Vector Store: `chromadb` (`PersistentClient`).
- Embeddings: OpenAI (Standard `text-embedding-3-large`, konfigurierbar).

### 4.2 Datenmodell

#### Dokument-Level

| Feld | Typ | Beschreibung |
| --- | --- | --- |
| `document_id` | `str` | Interne ID (z. B. Hash aus Pfad + Timestamp). |
| `source_path` | `str` | Pfad/URI der Originaldatei. |
| `collection` | `str` | `doctrine`, `aar`, `scenario`, `intel`. |
| `title` | `str` | Dokumenttitel. |
| `year` | `int \| null` | Erscheinungsjahr. |
| `doctrine` | `str \| null` | Z. B. NATO, UK MoD, RAND. |
| `tags` | `list[str]` | Tags wie `COA`, `urban`, `winter`. |

#### Chunk-Level (Chroma-Eintrag)

- `id`, `text`, `metadata` (inkl. Dokument-Infos, `chunk_index`, `chunk_count`).

### 4.3 Ingestion

1. Dateien scannen (PDF/DOCX/TXT/MD).
2. Text extrahieren (pypdf, python-docx, textract/TXT-Fallback).
3. Chunking (512–1024 Token, Overlap).
4. Metadaten extrahieren (Pfad/Config).
5. Embeddings via OpenAI holen.
6. Chroma updaten (idempotent; alte Chunks ersetzen).

### 4.4 MCP-Tools (API-Spezifikation)

#### 4.4.1 `search_wargame_docs`

- Semantische Suche mit optionalen Collection-Filtern und Score-Grenze.
- Input: Query, `top_k`, `collections`, `min_score`.
- Output: `results` mit Chunk-Inhalt, Score und Metadaten.

#### 4.4.2 `get_doc_span`

- Liefert mehrere Chunks um einen Treffer herum.
- Input: `document_id`, `center_chunk_index`, `span`.
- Output: Liste an Chunks (`chunk_index`, `text`, `metadata`).

#### 4.4.3 `list_collections`

- Listet Collections mit Namen, `document_count`, Beschreibung.

#### 4.4.4 `health_check`

- Prüft DB-Verbindung; Output `status` (`ok`, `degraded`, `error`) + `details`.

## 5. Memory-MCP – „mem0-mcp“

### 5.1 Grundkonzept

Memories speichern User-Präferenzen, Szenario-Episoden und Agent-Heuristiken. Backend: Mem0.

### 5.2 Datenmodell

- `memory_id`, `user_id`, `scope` (`user`, `scenario`, `agent`), `memory`, `tags`, `source`, `created_at`, `importance`.

### 5.3 MCP-Tools

#### 5.3.1 `memory_search`

- Input: `query`, `user_id`, optional `limit`, `scopes`.
- Output: `results` mit Memory-Text, Score, User, Scope, Tags, Source, `created_at`.

#### 5.3.2 `memory_add`

- Input: `user_id`, `scope`, `memory`, `tags`, `source`.
- Output: `memory_id`, `status="created"`.

#### 5.3.3 `memory_delete`

- Input: `memory_id`.
- Output: `status` (`deleted`, `not_found`).

## 6. Agenten-Design (OpenAI)

- Modell: GPT-4.1.
- Temperatur: Analyse 0.2–0.4; kreativ 0.5–0.7.
- System Prompt: Rolle „Wargame-Analyst & Doctrine Advisor“ mit Zugriff auf MCP-Tools.
- Tool-Nutzung: erst Memory (`memory_search`), dann RAG (`search_wargame_docs`), beide kombinieren, bei neuen Erkenntnissen `memory_add`.
- Beispiel-Flow: Query „COA-Empfehlung urban defense“ → Memory- & RAG-Abfragen, Antwort mit Quellen, optional neue Memory.

## 7. Nicht-funktionale Anforderungen

- **Performance:** RAG-Query < 1 s (Top-K=8); Memory-Query < 500 ms.
- **Stabilität:** Bei Ausfällen klare Fehlerkommunikation; Agent halluziniert keine Doktrinen.
- **Sicherheit:** MCP-Tools nur Read; User-IDs pseudonymisiert.

## 8. Deployment & Konfiguration

- **Wargame-RAG-MCP:** Docker-Container, Volume `/data/wargame_rag`, ENV (`OPENAI_API_KEY`, `CHROMA_PATH`, `EMBEDDING_MODEL`).
- **Mem0-MCP:** Mem0-Cloud oder Self-Hosted; ENV (`MEM0_API_KEY`, `MEM0_BASE_URL`).
- **Agent-Konfiguration:** Tools `wargame-rag-mcp`, `mem0-mcp`, fixer System Prompt.

## 9. Observability

### 9.1 Logging

- Structured JSON mit `service`, `timestamp`, `level`, `message`, `correlation_id`, `agent_run_id`, `tool_name`, `user_id`, `latency_ms`, `status`.
- Events für Start/Ende von Tool-Calls, Fehler.

### 9.2 Metrics

- Prometheus-kompatibel: `mcp_tool_calls_total`, `mcp_tool_latency_ms`, `rag_search_results_count`, `memory_add_requests_total`, `openai_requests_total`, `openai_tokens_total`.

### 9.3 Distributed Tracing

- OpenTelemetry Spans (`agent_run`, `mcp_tool_call:*`, `db_query:chroma`, `http_call:mem0`, `http_call:openai`).

### 9.4 Alerts

- RAG-Latenz, Memory-Server down, OpenAI-Fehler, OpenAI-Quota.

## 10. Testing-Strategie

- **Unit-Tests:** Chunker, Chroma-Adapter, Metadaten-Parser; Mem0-Wrapper. Mocks für Chroma, Mem0, OpenAI.
- **Integrationstests:** docker-compose mit realem Chroma & Mem0; Fixture-Docs; definierte Queries.
- **E2E-Tests:** Mini-Agent, Golden-Path (memory_add → Frage → memory_search + Antwort).
- **RAG-Evaluation:** Goldenset (Top-3-Recall), optional RAGAS/LangSmith.

## 11. Chunking-Strategie

- Tokenizer: `tiktoken` (Embedding-Modell).
- Konfiguration: `CHUNK_SIZE_TOKENS=800`, `CHUNK_OVERLAP_TOKENS=200`, Methode „sliding_window“ plus Paragraph-Heuristiken.
- Listen/Tabellen/Code-Blöcke respektieren Grenzen; OCR-Chunks mit `ocr=true`.

## 12. Rate Limiting & Cost Control

- **OpenAI:** Limits für Tokens/Requests pro Minute, Backoff bei 429, Token-Accounting.
- **Memory:** `MAX_MEMORY_ADDS_PER_USER_PER_DAY`, `MAX_MEMORY_LENGTH_CHARS`, Status `rejected_quota`.
- **Kostenüberblick:** Ingestion Summary-Logs, Online `openai_tokens_total`.

## 13. Agent-Fehlerbehandlung & Circuit-Breaker

- `max_tool_iterations=10`, `max_consecutive_failed_tools=3`.
- Retry-Logik mit Exponential Backoff.
- Fallback-Strategien (nur Memory oder RAG, beide down → Fehler).
- Circuit-Breaker blockt Tools nach vielen Fehlern.

## 14. Memory-Dedup & Hygiene

- Dedup vor `memory_add` (Ähnlichkeit >= 0.9 → kein neuer Eintrag).
- Nachtjob für Konsolidierung, Importance Decay, TTL.
- Utility-Metriken: `memory_search_calls_total`, `memory_add_dedup_ratio`, `memory_hit_useful_ratio`.

## 15. Versioning & Schema-Evolution

- Tools mit Version (`v1`). Breaking Changes → neue Version parallel betreiben.
- Output-Schema: neue Felder optional mit Defaults.

## 16. Development-Setup

- `docker-compose` Stack: `chroma`, `wargame-rag-mcp`, `mem0`, `mem0-mcp`, optional `openai-mock`.
- Ermöglicht lokale E2E-Tests & Integration.

## 17. Metadata-Extraction Pipeline

- Quellen: Dateipfad, YAML neben Dokument, PDF-Metadaten, Dateiname.
- Validierung: Jahr 1900–2100, Collection-Set, Doctrine-Werte.
- Fallback: fehlende Pflichtfelder → Warnung, `collection="other"`.

## 18. Quick-Wins für v1 (MVP-Muss)

- Structured JSON Logging mit `correlation_id` & `tool_name`.
- `max_tool_iterations=10` enforced.
- Basis-E2E-Test (Agent nutzt RAG-Tool, optional Memory).
- Kosten- & Token-Logging pro Service pro Tag.
- Chunking mit `CHUNK_SIZE=800`, `OVERLAP=200`, `tiktoken`-basiert.

