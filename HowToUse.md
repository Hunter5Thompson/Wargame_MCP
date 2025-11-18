# Wargame MCP - Anleitung & Dokumentation

## 📋 Inhaltsverzeichnis

1. [Überblick](#überblick)
2. [Voraussetzungen](#voraussetzungen)
3. [Schnellstart](#schnellstart)
4. [Architektur](#architektur)
5. [Konfiguration](#konfiguration)
6. [Verwendung](#verwendung)
7. [Entwicklung](#entwicklung)
8. [Troubleshooting](#troubleshooting)
9. [API-Referenz](#api-referenz)

---

## 🎯 Überblick

**Wargame MCP** ist ein vollständiges Knowledge & Memory System für militärische Wargaming-Szenarien. Das System kombiniert:

- **RAG (Retrieval-Augmented Generation)** mit ChromaDB für semantische Dokumentensuche
- **Memory-Layer** mit Mem0 für langfristige Erinnerungen und Präferenzen
- **OpenAI Agent-Integration** für intelligente Analyse und Entscheidungsfindung

### ✨ Features

- 🐳 **Vollständig containerisiert** - Alle Services in Docker, keine lokale Installation nötig
- 🔍 **Semantische Suche** - RAG-basierte Dokumentensuche mit Embeddings
- 🧠 **Memory-Management** - Persistente Speicherung von User-Präferenzen und Episoden
- 📊 **Strukturiertes Logging** - JSON-basierte Logs mit Correlation-IDs
- 🔧 **Einfache Bedienung** - Makefile mit allen wichtigen Befehlen
- 🛡️ **Produktionsbereit** - Health-Checks, Error-Handling, Thread-Safety

---

## 📦 Voraussetzungen

### Minimal

- **Docker** >= 20.10
- **Docker Compose** >= 2.0
- **Make** (optional, aber empfohlen)

### Für lokale Entwicklung (ohne Docker)

- **Python** >= 3.11
- **pip** oder **uv**
- **Git**

### API-Schlüssel (optional)

- **OpenAI API Key** - Für echte Embeddings und Agent-Funktionalität
  - Ohne API-Key: Fake-Embeddings für Tests verfügbar
  - Mit API-Key: Volle Funktionalität

---

## 🚀 Schnellstart

### Option A: Mit Make (empfohlen)

```bash
# 1. Repository klonen
git clone <repository-url>
cd Wargame_MCP

# 2. Konfiguration erstellen
make setup
# Bearbeite .env und füge deinen OPENAI_API_KEY hinzu

# 3. Alles starten und initialisieren
make init

# Das wars! System läuft jetzt.
```

### Option B: Manuell mit Docker Compose

```bash
# 1. Repository klonen
git clone <repository-url>
cd Wargame_MCP

# 2. Umgebungsvariablen konfigurieren
cp .env.example .env
# Bearbeite .env und füge deinen OPENAI_API_KEY hinzu

# 3. Services starten
docker-compose up -d

# 4. Beispieldokumente einlesen
docker-compose exec wargame-mcp wargame-mcp ingest /app/examples/sample_docs --fake-embeddings

# 5. Gesundheitscheck
docker-compose exec wargame-mcp wargame-mcp health-check
```

### Option C: Lokale Installation (ohne Docker)

```bash
# 1. Repository klonen
git clone <repository-url>
cd Wargame_MCP

# 2. Virtuelle Umgebung erstellen
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# 3. Paket installieren
pip install -e .

# 4. Umgebungsvariablen setzen
export CHROMA_PATH="./data/chroma"
export OPENAI_API_KEY="sk-..."  # optional

# 5. Dokumente einlesen
wargame-mcp ingest examples/sample_docs --fake-embeddings

# 6. Suchen
wargame-mcp search "urban defense" --fake-embeddings
```

---

## 🏗️ Architektur

### System-Komponenten

```
┌─────────────────────────────────────────────────────────────┐
│                      Docker Compose Stack                    │
├─────────────────────────────────────────────────────────────┤
│                                                               │
│  ┌──────────────┐      ┌──────────────┐      ┌───────────┐ │
│  │   ChromaDB   │      │     Mem0     │      │  Nginx    │ │
│  │  Vector DB   │      │  Memory DB   │      │  Proxy    │ │
│  │  Port: 8000  │      │  Port: 8080  │      │ (optional)│ │
│  └──────┬───────┘      └──────┬───────┘      └─────┬─────┘ │
│         │                     │                     │        │
│         └─────────┬───────────┘                     │        │
│                   │                                 │        │
│         ┌─────────▼──────────┐                      │        │
│         │   Wargame MCP App  │◄─────────────────────┘        │
│         │   Port: 8888       │                               │
│         │   • CLI Tools      │                               │
│         │   • MCP Server     │                               │
│         │   • Agent Bridge   │                               │
│         └────────────────────┘                               │
│                                                               │
└─────────────────────────────────────────────────────────────┘
```

### Datenfluss

1. **Ingestion**
   - Dokumente → Chunking → Embeddings → ChromaDB

2. **Suche**
   - Query → Embedding → ChromaDB → Ranked Results

3. **Memory**
   - Events → Mem0 → Persistent Storage
   - Query → Mem0 → Relevant Memories

4. **Agent**
   - User Query → OpenAI Agent → MCP Tools → Response

---

## ⚙️ Konfiguration

### Umgebungsvariablen

Alle Konfigurationen erfolgen über `.env`. Kopiere `.env.example` und passe an:

#### OpenAI-Konfiguration

```bash
# Pflicht für echte Embeddings und Agent-Funktionalität
OPENAI_API_KEY=sk-your-api-key-here

# Optional: Custom Endpoint (z.B. Azure OpenAI)
OPENAI_BASE_URL=https://api.openai.com/v1

# Embedding-Modell
EMBEDDING_MODEL=text-embedding-3-large
```

#### ChromaDB-Konfiguration

```bash
CHROMA_PATH=/data/chroma
CHROMA_COLLECTION=wargame_docs
```

#### Mem0-Konfiguration

```bash
# Service URL (Docker: http://mem0:8080, lokal: http://localhost:8080)
MEM0_BASE_URL=http://mem0:8080

# Optional: API Key für Mem0 Cloud
MEM0_API_KEY=your-mem0-api-key

# Defaults
MEM0_DEFAULT_LIMIT=10
MEM0_DEFAULT_SCOPE=user
```

#### Chunking-Konfiguration

```bash
CHUNK_SIZE_TOKENS=800
CHUNK_OVERLAP_TOKENS=200
```

### Docker-Ports

Standardmäßig werden folgende Ports verwendet:

- **8000** - ChromaDB
- **8080** - Mem0
- **8888** - Wargame MCP (für zukünftige API)

Änderbar in `docker-compose.yml`.

---

## 💻 Verwendung

### Mit Make (einfachste Methode)

```bash
# Alle verfügbaren Befehle anzeigen
make help

# Services starten
make up

# Logs anzeigen
make logs

# Health-Check
make health

# Dokumente einlesen
make ingest

# Mit echten Embeddings einlesen
make ingest-real

# Suchen
make search

# Shell im Container öffnen
make shell

# Services stoppen
make down

# Alles löschen (inkl. Daten)
make clean
```

### Direkt mit Docker Compose

```bash
# Services starten
docker-compose up -d

# Logs anzeigen
docker-compose logs -f wargame-mcp

# Shell öffnen
docker-compose exec wargame-mcp bash

# In der Shell:
wargame-mcp health-check
wargame-mcp list-collections
wargame-mcp search "urban defense" --fake-embeddings

# Services stoppen
docker-compose down
```

### CLI-Befehle

#### Ingestion

```bash
# Mit Fake-Embeddings (kein API-Key nötig)
wargame-mcp ingest <verzeichnis> --fake-embeddings

# Mit echten OpenAI Embeddings
wargame-mcp ingest <verzeichnis>

# Beispiel
wargame-mcp ingest /app/examples/sample_docs --fake-embeddings
```

#### Suche

```bash
# Basis-Suche
wargame-mcp search "deine Suchanfrage"

# Mit Parametern
wargame-mcp search "urban defense" --top-k 10 --min-score 0.5

# Mit Collection-Filter
wargame-mcp search "doctrine" --collections doctrine,aar

# Mit Fake-Embeddings
wargame-mcp search "query" --fake-embeddings
```

#### Collections

```bash
# Alle Collections auflisten
wargame-mcp list-collections
```

#### Health-Check

```bash
# System-Status prüfen
wargame-mcp health-check
```

---

## 🛠️ Entwicklung

### Lokale Entwicklung

```bash
# Dependencies installieren (mit Dev-Tools)
make dev-install

# Oder manuell:
pip install -e ".[dev]"

# Tests ausführen
make test-local

# Linting
make lint

# Code formatieren
make format

# Type-Checking
make type-check

# Alle Quality-Checks
make qa
```

### Tests

```bash
# In Docker
make test

# Lokal
pytest tests/ -v

# Mit Coverage
pytest tests/ -v --cov=src/wargame_mcp --cov-report=html

# Coverage-Report ansehen
open htmlcov/index.html
```

### Projekt-Struktur

```
Wargame_MCP/
├── src/wargame_mcp/          # Hauptcode
│   ├── __init__.py
│   ├── cli.py                # CLI-Interface
│   ├── config.py             # Konfiguration
│   ├── chunking.py           # Text-Chunking
│   ├── embeddings.py         # Embedding-Provider
│   ├── vectorstore.py        # ChromaDB-Interface
│   ├── mcp_tools.py          # RAG MCP-Tools
│   ├── memory_tools.py       # Memory MCP-Tools
│   ├── mem0_client.py        # Mem0 HTTP-Client
│   ├── agent.py              # OpenAI Agent-Bridge
│   ├── server.py             # MCP Server
│   └── ...
├── tests/                    # Tests
│   ├── test_mcp_tools.py
│   ├── test_memory_tools.py
│   └── ...
├── examples/                 # Beispiel-Dokumente
│   └── sample_docs/
├── docs/                     # Dokumentation
│   └── PRD.md               # Product Requirements
├── docker-compose.yml        # Service-Orchestrierung
├── Dockerfile               # App-Container
├── Makefile                 # Convenience-Commands
├── pyproject.toml           # Python-Konfiguration
├── .env.example             # Umgebungsvariablen-Template
└── HowToUse.md             # Diese Datei
```

---

## 🔧 Troubleshooting

### Problem: Services starten nicht

```bash
# Logs prüfen
make logs

# Oder einzelne Services:
docker-compose logs chromadb
docker-compose logs mem0
docker-compose logs wargame-mcp

# Health-Status prüfen
make health
```

### Problem: ChromaDB-Fehler

```bash
# ChromaDB-Daten zurücksetzen
make clean-data
make up
make ingest
```

### Problem: Mem0 nicht erreichbar

```bash
# Mem0-Container neu starten
docker-compose restart mem0

# Logs prüfen
docker-compose logs mem0

# Health-Check
curl http://localhost:8080/health
```

### Problem: "MEM0_BASE_URL is not configured"

**Lösung:** Stelle sicher, dass `.env` existiert und `MEM0_BASE_URL` gesetzt ist:

```bash
# Für Docker:
MEM0_BASE_URL=http://mem0:8080

# Für lokale Installation:
MEM0_BASE_URL=http://localhost:8080
```

### Problem: OpenAI API-Fehler

```bash
# API-Key prüfen
echo $OPENAI_API_KEY

# Für Tests ohne API-Key: Fake-Embeddings nutzen
wargame-mcp ingest examples/sample_docs --fake-embeddings
wargame-mcp search "query" --fake-embeddings
```

### Problem: "Permission denied" beim Ingest

**Lösung:** Container läuft als User `wargame` (UID 1000). Stelle sicher, dass Volumes korrekte Berechtigungen haben:

```bash
# Data-Verzeichnis erstellen
mkdir -p data/chroma
chmod -R 777 data/  # Für Development

# Oder mit Docker:
docker-compose down
docker volume rm wargame-chroma-data wargame-mem0-data
docker-compose up -d
```

### Problem: Tests schlagen fehl

```bash
# Dependencies neu installieren
pip install -e ".[dev]"

# Oder in Docker:
docker-compose exec wargame-mcp pip install -e ".[dev]"
docker-compose exec wargame-mcp pytest tests/ -v
```

---

## 📚 API-Referenz

### MCP RAG-Tools

#### `search_wargame_docs`

Semantische Suche in Wargaming-Dokumenten.

**Parameter:**
- `query` (str): Suchanfrage
- `top_k` (int, default=8): Anzahl Ergebnisse
- `min_score` (float, default=0.0): Minimale Ähnlichkeit
- `collections` (list[str], optional): Filter auf Collections

**Rückgabe:**
```json
{
  "results": [
    {
      "chunk_id": "...",
      "text": "...",
      "score": 0.85,
      "metadata": {
        "document_id": "...",
        "title": "...",
        "collection": "doctrine",
        "chunk_index": 5
      }
    }
  ]
}
```

#### `get_doc_span`

Holt mehrere zusammenhängende Chunks aus einem Dokument.

**Parameter:**
- `document_id` (str): Dokument-ID
- `center_chunk_index` (int): Mittlerer Chunk
- `span` (int, default=2): Anzahl Chunks um Zentrum herum

**Rückgabe:**
```json
{
  "chunks": [
    {
      "chunk_index": 4,
      "text": "...",
      "metadata": {...}
    },
    ...
  ]
}
```

#### `list_collections`

Listet alle verfügbaren Collections.

**Rückgabe:**
```json
{
  "collections": [
    {
      "name": "doctrine",
      "document_count": 42,
      "description": "Military doctrine documents"
    }
  ]
}
```

#### `health_check`

Prüft System-Gesundheit.

**Rückgabe:**
```json
{
  "status": "ok",
  "details": {
    "chromadb": "connected",
    "collections": ["wargame_docs"]
  }
}
```

### Memory-Tools

#### `memory_search`

Sucht in gespeicherten Memories.

**Parameter:**
- `query` (str): Suchanfrage
- `user_id` (str): User-ID
- `limit` (int, default=5): Max. Ergebnisse
- `scopes` (list[str], optional): Filter auf Scopes

**Rückgabe:**
```json
{
  "results": [
    {
      "memory_id": "...",
      "memory": "User prefers detailed COA analysis",
      "score": 0.92,
      "user_id": "user-123",
      "scope": "user",
      "tags": ["preference"],
      "created_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

#### `memory_add`

Fügt neues Memory hinzu.

**Parameter:**
- `user_id` (str): User-ID
- `memory` (str): Memory-Text
- `scope` (str, default="user"): Scope (user, scenario, agent)
- `tags` (list[str], optional): Tags
- `source` (str, optional): Quelle

**Rückgabe:**
```json
{
  "memory_id": "mem-xyz",
  "status": "created"
}
```

#### `memory_delete`

Löscht ein Memory.

**Parameter:**
- `memory_id` (str): Memory-ID

#### `memory_list`

Listet Memories für einen User.

**Parameter:**
- `user_id` (str): User-ID
- `limit` (int, default=5): Max. Ergebnisse
- `scope` (str, optional): Filter auf Scope
- `tags` (list[str], optional): Filter auf Tags

---

## 🎓 Beispiele

### Beispiel 1: Vollständiger Workflow

```bash
# 1. System starten
make init

# 2. Dokumente einlesen
make ingest

# 3. Suchen
docker-compose exec wargame-mcp wargame-mcp search "urban defense doctrine"

# 4. Collections anzeigen
docker-compose exec wargame-mcp wargame-mcp list-collections

# 5. System-Status
make health
```

### Beispiel 2: Entwicklung mit lokalen Tests

```bash
# Dev-Dependencies installieren
make dev-install

# Lokale ChromaDB starten (ohne Docker)
chroma run --path ./data/chroma &

# App lokal ausführen
export CHROMA_PATH=./data/chroma
export OPENAI_API_KEY=sk-...

# Ingest
wargame-mcp ingest examples/sample_docs

# Suchen
wargame-mcp search "urban warfare"

# Tests
make test-local
```

### Beispiel 3: Agent-Integration (Python)

```python
from wargame_mcp.agent import WargameAssistantAgent, AgentConfig, create_openai_client

# Client erstellen
client = create_openai_client(api_key="sk-...")

# Agent konfigurieren
config = AgentConfig(
    model="gpt-4o",
    temperature=0.3
)

# Agent erstellen
agent = WargameAssistantAgent(client=client, config=config)

# Frage stellen
response = agent.run_conversation(
    question="What are the key lessons from Baltic Shield exercises regarding urban defense?",
    user_id="analyst-001",
    correlation_id="query-123"
)

print(response)
```

---

## 📊 Monitoring

### Ressourcen-Nutzung

```bash
# Live-Stats
make stats

# Oder:
docker stats
```

### Logs

```bash
# Alle Logs
make logs

# Nur App
make logs-app

# Nur ChromaDB
make logs-chroma

# Nur Mem0
make logs-mem0
```

### Backup & Restore

```bash
# Backup erstellen
make backup

# Backup wiederherstellen (ACHTUNG: Überschreibt Daten!)
make restore
```

---

## 🔒 Sicherheit

### Best Practices

1. **API-Keys schützen**
   - `.env` nie in Git committen
   - Nutze `.env.example` als Template
   - Verwende Secrets-Manager in Production

2. **Netzwerk-Isolation**
   - Services laufen in eigenem Docker-Netzwerk
   - Nur notwendige Ports nach außen

3. **Non-Root-Container**
   - App läuft als User `wargame` (UID 1000)
   - Minimale Berechtigungen

4. **Input-Validation**
   - Type-Checking in allen Tool-Calls
   - Error-Handling für ungültige Parameter

---

## 📈 Roadmap & TODOs

### ✅ Implementiert (v0.2.0)

- [x] Vollständige Docker-Orchestrierung
- [x] ChromaDB-Integration
- [x] Mem0-Integration
- [x] MCP Server für RAG & Memory
- [x] OpenAI Agent-Bridge
- [x] Strukturiertes Logging
- [x] Health-Checks
- [x] Error-Handling
- [x] Thread-Safety
- [x] CLI-Tools
- [x] Tests

### 🚧 In Arbeit

- [ ] Web-UI (Streamlit/Gradio)
- [ ] Prometheus Metrics
- [ ] OpenTelemetry Tracing
- [ ] Memory-Deduplication
- [ ] Batch-Ingestion mit Fortschrittsanzeige
- [ ] PDF/DOCX Parser-Verbesserungen

### 📋 Geplant

- [ ] Kubernetes Deployment
- [ ] CI/CD Pipeline
- [ ] Performance-Optimierungen
- [ ] Multi-User-Support
- [ ] RBAC (Role-Based Access Control)
- [ ] Audit-Logs
- [ ] Rate-Limiting
- [ ] Query-Caching

---

## 🤝 Support & Beitrag

### Fragen?

1. Lies diese Dokumentation
2. Prüfe [docs/PRD.md](docs/PRD.md) für Details
3. Siehe [Troubleshooting](#troubleshooting)

### Bug gefunden?

1. Prüfe ob der Bug schon bekannt ist
2. Erstelle ein Issue mit:
   - Beschreibung des Problems
   - Schritte zur Reproduktion
   - Erwartetes vs. tatsächliches Verhalten
   - Logs/Screenshots

### Contribution

Pull Requests sind willkommen! Bitte:
- Folge dem bestehenden Code-Style
- Füge Tests hinzu
- Aktualisiere die Dokumentation
- Lasse `make qa` durchlaufen

---

## 📄 Lizenz

[Hier Lizenz einfügen]

---

## 🙏 Danksagungen

Dieses Projekt nutzt:
- [ChromaDB](https://www.trychroma.com/) - Vector Database
- [Mem0](https://mem0.ai/) - Memory Layer
- [OpenAI](https://openai.com/) - LLM & Embeddings
- [Typer](https://typer.tiangolo.com/) - CLI Framework
- [Rich](https://rich.readthedocs.io/) - Terminal Formatting

---

**Version:** 0.2.0
**Letzte Aktualisierung:** 2025-01-18
**Status:** Production-Ready ✅
