# Simple Makefile for Solo Development
# ====================================

.PHONY: help install test lint format run clean

help: ## Show this help
	@echo "🚀 Examify API - Simple Commands"
	@echo "================================"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

install: ## Install dependencies
	@echo "📦 Installing dependencies..."
	cd backend/app && poetry install --with dev

run: ## Start development server
	@echo "🚀 Starting development server..."
	docker compose -f docker-compose-dev.yml up

run-bg: ## Start development server in background
	@echo "🚀 Starting development server in background..."
	docker compose -f docker-compose-dev.yml up -d

stop: ## Stop development server
	@echo "🛑 Stopping development server..."
	docker compose -f docker-compose-dev.yml down

##@ Code Quality

format: ## Format code
	@echo "🎨 Formatting code..."
	cd backend/app && poetry run black .
	cd backend/app && poetry run ruff --fix .

lint: ## Check code quality
	@echo "🔍 Checking code quality..."
	cd backend/app && poetry run black --check .
	cd backend/app && poetry run ruff check .
	cd backend/app && poetry run mypy . || true

##@ Testing

test: ## Run tests
	@echo "🧪 Running tests..."
	cd backend/app && poetry run pytest -v

test-cov: ## Run tests with coverage
	@echo "🧪 Running tests with coverage..."
	cd backend/app && poetry run pytest --cov=app --cov-report=html -v

##@ Database

init-db: ## Initialize database with sample data
	@echo "🗄️ Initializing database..."
	docker compose -f docker-compose-dev.yml exec fastapi_server python app/initial_data.py

migrate: ## Run database migrations
	@echo "🔄 Running migrations..."
	docker compose -f docker-compose-dev.yml exec fastapi_server alembic upgrade head

##@ Utilities

logs: ## Show application logs
	@echo "📋 Showing logs..."
	docker compose -f docker-compose-dev.yml logs -f fastapi_server

clean: ## Clean up
	@echo "🧹 Cleaning up..."
	docker system prune -f
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

status: ## Show status
	@echo "📊 Status:"
	@docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(fastapi|database|redis)" || echo "No containers running"
	@echo ""
	@echo "🌐 Available at: http://localhost/api/v1/docs"

##@ Git Helpers

commit: ## Quick commit (use: make commit m="your message")
	@if [ -z "$(m)" ]; then echo "Usage: make commit m=\"your message\""; exit 1; fi
	git add .
	git commit -m "$(m)"
	git push

quick-fix: format lint ## Format, lint, and show status
	@echo "✅ Code is ready!"
