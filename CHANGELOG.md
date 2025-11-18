# Changelog

All notable changes to the Wargame MCP project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.2.0] - 2025-01-18

### 🎉 Major Release - Production Ready

This release brings critical bug fixes, complete Docker orchestration, and SOTA modernization.

### Added

- 🐳 **Complete Docker orchestration** with docker-compose.yml
- 📦 **Multi-stage Dockerfile** for optimized production images
- 🔧 **Makefile** with 30+ convenience commands
- 📚 **Comprehensive HowToUse.md** documentation
- 🔒 **Thread-safe singleton** pattern for Mem0 client
- ✅ **Comprehensive error handling** in ingestion pipeline
- 🛡️ **Type-safe parameter conversion** in agent tools
- 🌐 **Nginx reverse proxy** support (optional profile)
- 🔍 **Health checks** for all services
- 📊 **Structured logging** improvements
- 🚀 **GitHub Actions CI/CD** pipeline
- 🧪 **Enhanced test configuration** (pytest.ini, ruff.toml)
- 💾 **Backup/restore** functionality via Makefile

### Fixed

- 🐛 **CRITICAL:** Missing Mem0 configuration settings in config.py
- 🐛 **CRITICAL:** Unsafe type conversions in agent.py (int/float without error handling)
- 🐛 **CRITICAL:** No error handling in ingest.py (single file failure crashed entire batch)
- 🐛 **CRITICAL:** Thread-unsafe global state in mem0_client.py (race conditions)
- 🔧 Missing dependencies in pyproject.toml (httpx, openai)
- 📝 Improved error messages with colored output
- 🎨 Better logging format with success/failure indicators

### Changed

- 📦 Version bump to 0.2.0
- 🔄 Enhanced dependencies with dev tools (pytest-cov, ruff, mypy)
- 🔐 Non-root Docker user (wargame, UID 1000)
- 🌐 Service orchestration with proper health checks and dependencies
- 📝 Expanded .gitignore with comprehensive patterns
- 🏗️ Improved project structure and modularity

### Security

- 🔒 Non-root container execution
- 🔑 API keys properly handled via environment variables
- 🛡️ Input validation in all tool calls
- 🔐 Network isolation via Docker networks

### Documentation

- 📖 Complete HowToUse.md with examples
- 📋 Updated README.md with Docker quickstart
- 📝 Inline code documentation improvements
- 🎓 Troubleshooting guide
- 📚 API reference documentation

### Performance

- ⚡ Multi-stage Docker builds for smaller images
- 🚀 Parallel dependency installation
- 💾 Proper volume management for persistent data

## [0.1.0] - 2025-01-15

### Initial Release

- ✨ Basic MCP RAG server implementation
- 🔍 Semantic search with ChromaDB
- 🧠 Memory integration with Mem0
- 🤖 OpenAI agent bridge
- 📦 CLI tools (ingest, search, health-check)
- 🧪 Basic test suite
- 📝 PRD documentation

---

## Upgrade Guide

### From 0.1.0 to 0.2.0

1. **Update configuration:**
   ```bash
   cp .env.example .env
   # Add your API keys and configuration
   ```

2. **Rebuild Docker images:**
   ```bash
   make clean
   make build
   make up
   ```

3. **Re-ingest documents** (optional, but recommended):
   ```bash
   make ingest
   ```

4. **Update local installation:**
   ```bash
   pip install -e ".[dev]"
   ```

### Breaking Changes

None in this release. All changes are backwards compatible.

---

## Contributors

- **Claude Code** - Initial implementation and SOTA modernization
- **Wargame Team** - Project vision and requirements

---

## Links

- [GitHub Repository](https://github.com/your-org/wargame-mcp)
- [Documentation](./HowToUse.md)
- [Product Requirements](./docs/PRD.md)
