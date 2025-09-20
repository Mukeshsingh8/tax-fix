# TaxFix Multi-Agent System Makefile

.PHONY: help install setup start start-backend start-frontend clean test lint

help: ## Show this help message
	@echo "TaxFix Multi-Agent System"
	@echo "========================="
	@echo ""
	@echo "Available commands:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[36m%-20s\033[0m %s\n", $$1, $$2}'

install: ## Install dependencies
	pip install -r requirements.txt

setup: ## Setup environment and configuration
	@echo "Setting up TaxFix environment..."
	@if [ ! -f .env ]; then \
		cp config/env.example .env; \
		echo "✅ Created .env file from template"; \
		echo "⚠️  Please edit .env with your API keys and configuration"; \
	else \
		echo "✅ .env file already exists"; \
	fi
	@echo "✅ Setup complete!"

start: ## Start both backend and frontend
	python scripts/start_app.py

start-backend: ## Start backend only
	python scripts/start_backend.py

start-frontend: ## Start frontend only
	python scripts/start_frontend.py

clean: ## Clean up temporary files
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name "*.egg-info" -exec rm -rf {} +
	rm -rf .pytest_cache
	rm -rf .coverage

test: ## Run tests
	python -m pytest tests/ -v

lint: ## Run linting
	flake8 src/ apps/ scripts/
	black --check src/ apps/ scripts/

format: ## Format code
	black src/ apps/ scripts/
	isort src/ apps/ scripts/

dev: ## Start development environment with hot reload
	@echo "Starting development environment..."
	@echo "Backend: http://localhost:8000"
	@echo "Frontend: http://localhost:8501"
	@echo "API Docs: http://localhost:8000/docs"
	python scripts/start_app.py
