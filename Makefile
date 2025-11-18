.PHONY: help build up down restart logs clean test lint format install dev-install health ingest

# Default target
.DEFAULT_GOAL := help

# Colors for output
CYAN := \033[0;36m
GREEN := \033[0;32m
YELLOW := \033[0;33m
RED := \033[0;31m
NC := \033[0m # No Color

help: ## Show this help message
	@echo "$(CYAN)Wargame MCP - Available Commands$(NC)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(NC) %s\n", $$1, $$2}'
	@echo ""

# =============================================================================
# Docker Operations
# =============================================================================

build: ## Build all Docker images
	@echo "$(CYAN)Building Docker images...$(NC)"
	docker-compose build

up: ## Start all services
	@echo "$(CYAN)Starting services...$(NC)"
	docker-compose up -d
	@echo "$(GREEN)Services started successfully!$(NC)"
	@make health

up-proxy: ## Start all services with Nginx reverse proxy
	@echo "$(CYAN)Starting services with proxy...$(NC)"
	docker-compose --profile with-proxy up -d
	@echo "$(GREEN)Services started successfully!$(NC)"

down: ## Stop all services
	@echo "$(YELLOW)Stopping services...$(NC)"
	docker-compose down
	@echo "$(GREEN)Services stopped.$(NC)"

restart: ## Restart all services
	@echo "$(CYAN)Restarting services...$(NC)"
	@make down
	@make up

logs: ## Show logs from all services
	docker-compose logs -f

logs-app: ## Show logs from wargame-mcp application
	docker-compose logs -f wargame-mcp

logs-chroma: ## Show logs from ChromaDB
	docker-compose logs -f chromadb

logs-mem0: ## Show logs from Mem0
	docker-compose logs -f mem0

ps: ## Show status of all services
	@echo "$(CYAN)Service Status:$(NC)"
	@docker-compose ps

clean: ## Remove containers, volumes, and networks
	@echo "$(RED)Removing all containers, volumes, and networks...$(NC)"
	docker-compose down -v
	@echo "$(GREEN)Cleanup complete.$(NC)"

clean-data: ## Remove all persistent data (WARNING: irreversible!)
	@echo "$(RED)WARNING: This will delete all your data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker volume rm wargame-chroma-data wargame-mem0-data || true; \
		rm -rf ./data; \
		echo "$(GREEN)Data removed.$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled.$(NC)"; \
	fi

# =============================================================================
# Health Checks
# =============================================================================

health: ## Check health of all services
	@echo "$(CYAN)Checking service health...$(NC)"
	@echo ""
	@echo "$(YELLOW)ChromaDB:$(NC)"
	@curl -s http://localhost:8000/api/v1/heartbeat || echo "$(RED)✗ ChromaDB not responding$(NC)"
	@echo ""
	@echo "$(YELLOW)Mem0:$(NC)"
	@curl -s http://localhost:8080/health || echo "$(RED)✗ Mem0 not responding$(NC)"
	@echo ""
	@echo "$(YELLOW)Wargame MCP:$(NC)"
	@docker-compose exec -T wargame-mcp wargame-mcp health-check || echo "$(RED)✗ Wargame MCP not responding$(NC)"
	@echo ""

# =============================================================================
# Application Operations
# =============================================================================

shell: ## Open shell in wargame-mcp container
	docker-compose exec wargame-mcp /bin/bash

ingest: ## Ingest example documents
	@echo "$(CYAN)Ingesting example documents...$(NC)"
	docker-compose exec wargame-mcp wargame-mcp ingest /app/examples/sample_docs --fake-embeddings
	@echo "$(GREEN)Ingestion complete!$(NC)"

ingest-real: ## Ingest with real OpenAI embeddings (requires API key)
	@echo "$(CYAN)Ingesting with real embeddings...$(NC)"
	docker-compose exec wargame-mcp wargame-mcp ingest /app/examples/sample_docs
	@echo "$(GREEN)Ingestion complete!$(NC)"

search: ## Search documents (example query)
	@echo "$(CYAN)Searching for 'urban defense'...$(NC)"
	docker-compose exec wargame-mcp wargame-mcp search "urban defense" --fake-embeddings

list-collections: ## List all collections
	docker-compose exec wargame-mcp wargame-mcp list-collections

# =============================================================================
# Development Operations
# =============================================================================

install: ## Install package locally (without Docker)
	pip install -e .

dev-install: ## Install package with dev dependencies
	pip install -e ".[dev]"

test: ## Run tests in Docker
	docker-compose exec wargame-mcp pytest tests/ -v

test-local: ## Run tests locally
	pytest tests/ -v --cov=src/wargame_mcp

lint: ## Run linting checks
	ruff check src/ tests/

format: ## Format code with ruff
	ruff format src/ tests/
	ruff check --fix src/ tests/

type-check: ## Run type checking with mypy
	mypy src/wargame_mcp

qa: format lint type-check ## Run all quality checks

# =============================================================================
# Monitoring & Debugging
# =============================================================================

stats: ## Show resource usage statistics
	docker stats --no-stream

inspect-chroma: ## Inspect ChromaDB data
	docker-compose exec chromadb ls -lah /chroma/chroma

inspect-mem0: ## Inspect Mem0 data
	docker-compose exec mem0 ls -lah /data

backup: ## Backup all data to ./backups
	@echo "$(CYAN)Creating backup...$(NC)"
	@mkdir -p backups
	@docker run --rm -v wargame-chroma-data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/chroma-$(shell date +%Y%m%d-%H%M%S).tar.gz -C /data .
	@docker run --rm -v wargame-mem0-data:/data -v $(PWD)/backups:/backup alpine tar czf /backup/mem0-$(shell date +%Y%m%d-%H%M%S).tar.gz -C /data .
	@echo "$(GREEN)Backup complete!$(NC)"

restore: ## Restore from latest backup
	@echo "$(RED)WARNING: This will overwrite current data!$(NC)"
	@read -p "Are you sure? [y/N] " -n 1 -r; \
	echo; \
	if [[ $$REPLY =~ ^[Yy]$$ ]]; then \
		docker run --rm -v wargame-chroma-data:/data -v $(PWD)/backups:/backup alpine sh -c "cd /data && tar xzf /backup/$$(ls -t /backup/chroma-*.tar.gz | head -1)"; \
		docker run --rm -v wargame-mem0-data:/data -v $(PWD)/backups:/backup alpine sh -c "cd /data && tar xzf /backup/$$(ls -t /backup/mem0-*.tar.gz | head -1)"; \
		echo "$(GREEN)Restore complete!$(NC)"; \
	else \
		echo "$(YELLOW)Cancelled.$(NC)"; \
	fi

# =============================================================================
# Setup & Configuration
# =============================================================================

setup: ## Initial setup (create .env from example)
	@if [ ! -f .env ]; then \
		cp .env.example .env; \
		echo "$(GREEN)Created .env file. Please edit it with your configuration.$(NC)"; \
	else \
		echo "$(YELLOW).env file already exists.$(NC)"; \
	fi

init: setup build up ingest ## Complete initialization (setup, build, start, ingest)
	@echo ""
	@echo "$(GREEN)╔════════════════════════════════════════════════════════════╗$(NC)"
	@echo "$(GREEN)║  Wargame MCP is ready!                                     ║$(NC)"
	@echo "$(GREEN)╠════════════════════════════════════════════════════════════╣$(NC)"
	@echo "$(GREEN)║  ChromaDB:    http://localhost:8000                        ║$(NC)"
	@echo "$(GREEN)║  Mem0:        http://localhost:8080                        ║$(NC)"
	@echo "$(GREEN)║  Wargame MCP: docker-compose exec wargame-mcp wargame-mcp ║$(NC)"
	@echo "$(GREEN)╚════════════════════════════════════════════════════════════╝$(NC)"
	@echo ""
