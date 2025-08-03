# Examify API - Development & CI/CD Makefile
# ============================================================================

.PHONY: help install test lint format security build deploy clean

# Default target
help: ## Show this help message
	@echo "🚀 Examify API - Development Commands"
	@echo "======================================"
	@awk 'BEGIN {FS = ":.*##"; printf "\nUsage:\n  make \033[36m<target>\033[0m\n"} /^[a-zA-Z_-]+:.*?##/ { printf "  \033[36m%-15s\033[0m %s\n", $$1, $$2 } /^##@/ { printf "\n\033[1m%s\033[0m\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Development

install: ## Install dependencies using Poetry
	@echo "📦 Installing dependencies..."
	cd backend/app && poetry install --with dev

install-prod: ## Install production dependencies only
	@echo "📦 Installing production dependencies..."
	cd backend/app && poetry install --only main

update: ## Update dependencies
	@echo "🔄 Updating dependencies..."
	cd backend/app && poetry update

##@ Code Quality

format: ## Format code with Black and sort imports
	@echo "🎨 Formatting code..."
	cd backend/app && poetry run black .
	cd backend/app && poetry run ruff --fix .

lint: ## Run linting checks
	@echo "🔍 Running linting checks..."
	cd backend/app && poetry run ruff check .
	cd backend/app && poetry run black --check .

type-check: ## Run type checking with MyPy
	@echo "🏷️ Running type checks..."
	cd backend/app && poetry run mypy .

quality: lint type-check ## Run all code quality checks

##@ Testing

test: ## Run unit tests
	@echo "🧪 Running unit tests..."
	cd backend/app && poetry run pytest -v

test-cov: ## Run tests with coverage
	@echo "🧪 Running tests with coverage..."
	cd backend/app && poetry run pytest --cov=app --cov-report=html --cov-report=term-missing -v

test-fast: ## Run tests in parallel (fast)
	@echo "⚡ Running fast tests..."
	cd backend/app && poetry run pytest -n auto -v

test-integration: ## Run integration tests
	@echo "🔗 Running integration tests..."
	docker compose -f docker-compose-test.yml up -d
	sleep 30
	cd backend/app && poetry run pytest test/integration/ -v
	docker compose -f docker-compose-test.yml down

##@ Security

security: ## Run security scans
	@echo "🔒 Running security scans..."
	cd backend/app && poetry add --group dev bandit[toml] safety
	cd backend/app && poetry run bandit -r . -f json -o bandit-report.json
	cd backend/app && poetry run safety check

security-fix: ## Fix security issues automatically where possible
	@echo "🔧 Fixing security issues..."
	cd backend/app && poetry update

##@ Docker

build: ## Build Docker images
	@echo "🐳 Building Docker images..."
	docker compose build

build-prod: ## Build production Docker images
	@echo "🐳 Building production Docker images..."
	docker compose -f docker-compose.yml build

run-dev: ## Run development environment
	@echo "🚀 Starting development environment..."
	docker compose -f docker-compose-dev.yml up

run-dev-build: ## Build and run development environment
	@echo "🚀 Building and starting development environment..."
	docker compose -f docker-compose-dev.yml up --build

run-prod: ## Run production environment
	@echo "🌟 Starting production environment..."
	docker compose up

run-test: ## Run test environment
	@echo "🧪 Starting test environment..."
	docker compose -f docker-compose-test.yml up

stop: ## Stop all containers
	@echo "🛑 Stopping all containers..."
	docker compose -f docker-compose-dev.yml down
	docker compose -f docker-compose-test.yml down
	docker compose down

##@ Database

init-db: ## Initialize database with sample data
	@echo "🗄️ Initializing database..."
	docker compose -f docker-compose-dev.yml exec fastapi_server python app/initial_data.py

migrate: ## Run database migrations
	@echo "🔄 Running database migrations..."
	docker compose -f docker-compose-dev.yml exec fastapi_server alembic upgrade head

migration: ## Create new migration
	@echo "📝 Creating new migration..."
	docker compose -f docker-compose-dev.yml exec fastapi_server alembic revision --autogenerate

clear-db: ## Clear database (development only)
	@echo "🧹 Clearing database..."
	docker compose -f docker-compose-dev.yml exec fastapi_server python app/clear_all_dummy.py

##@ Monitoring

logs: ## Show application logs
	@echo "📋 Showing application logs..."
	docker compose -f docker-compose-dev.yml logs -f fastapi_server

logs-all: ## Show all container logs
	@echo "📋 Showing all container logs..."
	docker compose -f docker-compose-dev.yml logs -f

health: ## Check application health
	@echo "🏥 Checking application health..."
	curl -f http://localhost/ || echo "❌ Application not responding"
	curl -f http://localhost/api/v1/openapi.json || echo "❌ API not responding"

##@ Performance

perf-test: ## Run performance tests
	@echo "⚡ Running performance tests..."
	cd performance-tests && locust -f locustfile.py --host=http://localhost --users=10 --spawn-rate=2 --run-time=60s --headless

load-test: ## Run load tests with custom parameters
	@echo "🚀 Running load tests..."
	@read -p "Enter host (default: http://localhost): " host; \
	read -p "Enter users (default: 50): " users; \
	read -p "Enter duration in seconds (default: 300): " duration; \
	cd performance-tests && locust -f locustfile.py \
		--host=$${host:-http://localhost} \
		--users=$${users:-50} \
		--spawn-rate=10 \
		--run-time=$${duration:-300}s \
		--html=load-test-report.html \
		--headless

##@ Deployment

deploy-staging: ## Deploy to staging environment
	@echo "🚀 Deploying to staging..."
	@echo "This will trigger the GitHub Actions deployment workflow"
	git push origin develop

deploy-prod: ## Deploy to production (requires tag)
	@echo "🌟 Deploying to production..."
	@read -p "Enter version tag (e.g., v1.0.0): " tag; \
	git tag $$tag && git push origin $$tag

##@ Utilities

clean: ## Clean up temporary files and containers
	@echo "🧹 Cleaning up..."
	docker system prune -f
	docker volume prune -f
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	find . -type d -name ".pytest_cache" -delete
	find . -type f -name ".coverage" -delete
	find . -type d -name "htmlcov" -delete

backup-db: ## Backup database (development)
	@echo "💾 Backing up database..."
	docker compose -f docker-compose-dev.yml exec database pg_dump -U postgres testdb > backup_$(shell date +%Y%m%d_%H%M%S).sql

restore-db: ## Restore database from backup
	@echo "📥 Restoring database..."
	@read -p "Enter backup file path: " backup; \
	docker compose -f docker-compose-dev.yml exec -T database psql -U postgres testdb < $$backup

docs: ## Generate and serve documentation
	@echo "📚 Generating documentation..."
	@echo "API Documentation available at: http://localhost/api/v1/docs"
	@echo "ReDoc available at: http://localhost/api/v1/redoc"

env-check: ## Check environment setup
	@echo "🔍 Checking environment setup..."
	@command -v docker >/dev/null 2>&1 || { echo "❌ Docker is not installed"; exit 1; }
	@command -v docker-compose >/dev/null 2>&1 || { echo "❌ Docker Compose is not installed"; exit 1; }
	@command -v poetry >/dev/null 2>&1 || { echo "❌ Poetry is not installed"; exit 1; }
	@test -f .env || { echo "❌ .env file not found"; exit 1; }
	@echo "✅ Environment setup looks good!"

##@ CI/CD

ci-test: ## Run CI tests locally
	@echo "🔄 Running CI tests locally..."
	$(MAKE) quality
	$(MAKE) security
	$(MAKE) test-cov

ci-build: ## Build for CI/CD
	@echo "🏗️ Building for CI/CD..."
	docker build -t examify-api:ci ./backend

pre-commit: ## Run pre-commit checks
	@echo "🔍 Running pre-commit checks..."
	$(MAKE) format
	$(MAKE) quality
	$(MAKE) test-fast
	@echo "✅ Pre-commit checks passed!"

##@ Information

status: ## Show project status
	@echo "📊 Examify API Status"
	@echo "===================="
	@echo "🐳 Docker containers:"
	@docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" | grep -E "(fastapi|database|redis|celery|minio|caddy)" || echo "No containers running"
	@echo ""
	@echo "🌐 Available endpoints:"
	@echo "  • API Root: http://localhost/"
	@echo "  • Swagger UI: http://localhost/api/v1/docs"
	@echo "  • ReDoc: http://localhost/api/v1/redoc"
	@echo "  • OpenAPI JSON: http://localhost/api/v1/openapi.json"

version: ## Show version information
	@echo "📋 Version Information"
	@echo "====================="
	@echo "Python: $(shell python --version 2>/dev/null || echo 'Not installed')"
	@echo "Poetry: $(shell poetry --version 2>/dev/null || echo 'Not installed')"
	@echo "Docker: $(shell docker --version 2>/dev/null || echo 'Not installed')"
	@echo "Docker Compose: $(shell docker compose version 2>/dev/null || echo 'Not installed')"
	@echo "Git: $(shell git --version 2>/dev/null || echo 'Not installed')"
