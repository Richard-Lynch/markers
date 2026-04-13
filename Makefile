.PHONY: help venv deps deps\:resolve deps\:install deps\:update test test\:cov lint format typecheck check build clean

VENV := .venv
UV := uv

help: ## Show this help
	@sed -n 's/^\([a-zA-Z_\\:-]*\):.*## \(.*\)/\1\t\2/p' $(MAKEFILE_LIST) | sed 's/\\:/:/g' | sort | awk -F '\t' '{printf "\033[36m%-20s\033[0m %s\n", $$1, $$2}'

# --- Environment ---

venv: ## Create virtual environment
	$(UV) venv $(VENV)

# --- Dependencies ---

deps\:resolve: ## Resolve and lock dependencies
	$(UV) lock

deps\:install: ## Install project with dev extras into venv
	$(UV) sync --extra dev

deps\:update: ## Update all dependencies and re-lock
	$(UV) lock --upgrade
	$(UV) sync --extra dev

deps: ## Alias for deps:install
	@$(MAKE) deps:install

# --- Testing ---

test: ## Run tests
	$(UV) run pytest tests/ -v

test\:cov: ## Run tests with coverage
	$(UV) run pytest tests/ --cov=markers --cov-report=term-missing --cov-report=html

# --- Linting & Formatting ---

lint: ## Run linters (ruff check + format check)
	$(UV) run ruff check src/ tests/ examples/
	$(UV) run ruff format --check src/ tests/ examples/

format: ## Auto-format code
	$(UV) run ruff format src/ tests/ examples/
	$(UV) run ruff check --fix src/ tests/ examples/

# --- Type Checking ---

typecheck: ## Run mypy on library and examples
	$(UV) run mypy src/markers/ examples/ --ignore-missing-imports

# --- All Checks ---

check: lint typecheck test ## Run all checks (lint, typecheck, test)

# --- Build ---

build: ## Build sdist and wheel
	$(UV) build

# --- Cleanup ---

clean: ## Clean build artifacts
	rm -rf dist/ build/ *.egg-info src/*.egg-info .tox .pytest_cache .mypy_cache .ruff_cache htmlcov .coverage coverage.xml
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
