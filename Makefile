# Simple Makefile for Solo Development - Examify API
# ===================================================

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
	@echo "🚀 Starting Examify API development server..."
	docker compose -f docker-compose-dev.yml up

run-bg: ## Start development server in background
	@echo "🚀 Starting Examify API development server in background..."
	docker compose -f docker-compose-dev.yml up -d

stop: ## Stop development server
	@echo "🛑 Stopping Examify API development server..."
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

test: ## Run tests (requires running containers)
	@echo "🧪 Running tests..."
	@echo "⚠️  Make sure containers are running: make run-bg"
	cd backend/app && poetry run pytest -v

test-local: ## Run tests with local test environment
	@echo "🧪 Setting up and running tests locally..."
	@echo "🔧 Starting test services..."
	@docker compose -f docker-compose-test.yml up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 10
	@echo "🧪 Running tests..."
	@cd backend/app && poetry run pytest -v || true
	@echo "🧹 Cleaning up test services..."
	@docker compose -f docker-compose-test.yml down

test-cov: ## Run tests with coverage
	@echo "🧪 Running tests with coverage..."
	@echo "⚠️  Make sure containers are running: make run-bg"
	cd backend/app && poetry run pytest --cov=app --cov-report=html -v

test-quick: ## Run tests quickly (stop on first failure)
	@echo "⚡ Running quick tests..."
	@echo "⚠️  Make sure containers are running: make run-bg"
	cd backend/app && poetry run pytest -v -x

##@ Database

init-db: ## Initialize database with sample data
	@echo "🗄️ Initializing Examify database..."
	docker compose -f docker-compose-dev.yml exec examify_api python app/initial_data.py

migrate: ## Run database migrations
	@echo "🔄 Running Examify database migrations..."
	docker compose -f docker-compose-dev.yml exec examify_api alembic upgrade head

##@ Utilities

logs: ## Show application logs
	@echo "📋 Showing Examify API logs..."
	docker compose -f docker-compose-dev.yml logs -f examify_api

clean: ## Clean up
	@echo "🧹 Cleaning up..."
	docker system prune -f
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete

status: ## Show status
	@echo "📊 Examify API Status:"
	@docker ps --format "table {{.Names}}\t{{.Status}}" | grep -E "(examify)" || echo "No Examify containers running"
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

##@ CI/CD Helpers

ci-test: ## Run tests like CI does (with fresh containers)
	@echo "🔄 Running tests like CI..."
	@echo "🧹 Cleaning up any existing containers..."
	@docker compose -f docker-compose-test.yml down -v 2>/dev/null || true
	@echo "🚀 Starting fresh test environment..."
	@docker compose -f docker-compose-test.yml up -d
	@echo "⏳ Waiting for services to be ready..."
	@sleep 15
	@echo "🧪 Running tests with CI environment..."
	@cd backend/app && \
		PROJECT_NAME="Examify API Test" \
		MODE="testing" \
		DATABASE_USER="testuser" \
		DATABASE_PASSWORD="testpass" \
		DATABASE_HOST="localhost" \
		DATABASE_PORT="5432" \
		DATABASE_NAME="testdb" \
		REDIS_HOST="localhost" \
		REDIS_PORT="6379" \
		ACCESS_TOKEN_EXPIRE_MINUTES="60" \
		OPENAI_API_KEY="test-key" \
		poetry run pytest -v --tb=short || true
	@echo "🧹 Cleaning up test environment..."
	@docker compose -f docker-compose-test.yml down -v

check-env: ## Check if environment is properly set up
	@echo "🔍 Checking Examify API environment setup..."
	@echo "📦 Poetry:"
	@cd backend/app && poetry --version || echo "❌ Poetry not found"
	@echo "🐳 Docker:"
	@docker --version || echo "❌ Docker not found"
	@echo "📋 Environment file:"
	@test -f .env && echo "✅ .env file exists" || echo "⚠️  .env file missing"
	@echo "🗄️  Examify containers:"
	@docker ps | grep -E "(examify)" && echo "✅ Examify containers running" || echo "⚠️  Examify containers not running - use 'make run-bg'"


backfill-slugs: ## Backfill missing slugs for existing records
	@echo "🔄 Backfilling missing slugs..."
	docker compose -f docker-compose-dev.yml exec examify_api python app/backfill_slugs.py
