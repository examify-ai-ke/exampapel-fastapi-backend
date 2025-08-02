#!/bin/bash

# 🧪 Examify API - Test Environment Setup
# This script helps you set up the environment for running tests locally

set -e

echo "🧪 SETTING UP EXAMIFY API TEST ENVIRONMENT"
echo "=========================================="
echo ""

# Create .env file with all required variables
echo "🔧 Creating test environment file..."
cat > .env << EOF
# Examify API Test Environment Configuration
PROJECT_NAME=Examify API Test
MODE=testing
API_VERSION=v1

# Database Configuration
DATABASE_USER=testuser
DATABASE_PASSWORD=testpass
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_NAME=testdb
DATABASE_CELERY_NAME=testdb

# Redis Configuration
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_PASSWORD=

# Authentication
ACCESS_TOKEN_EXPIRE_MINUTES=60
REFRESH_TOKEN_EXPIRE_MINUTES=1440

# External Services (Test Values)
OPENAI_API_KEY=test-key-for-testing
MINIO_ROOT_USER=testuser
MINIO_ROOT_PASSWORD=testpass
S3_BUCKET_NAME=test-bucket
MINIO_URL=localhost:9000

# Initial User
FIRST_SUPERUSER_EMAIL=admin@test.com
FIRST_SUPERUSER_PASSWORD=testpass

# Other Required Variables
EXT_ENDPOINT1=localhost
LOCAL_1=localhost
LOCAL_2=localhost
EOF

echo "✅ Test environment file created!"
echo ""

echo "🐳 Starting Examify API test services..."
docker compose -f docker-compose-test.yml up -d

echo ""
echo "⏳ Waiting for services to be ready..."
sleep 15

echo ""
echo "🧪 Testing database connection..."
if docker compose -f docker-compose-test.yml exec -T examify_database_test pg_isready -U testuser; then
    echo "✅ Database is ready!"
else
    echo "❌ Database not ready. Waiting a bit more..."
    sleep 10
fi

echo ""
echo "🎯 EXAMIFY API TEST ENVIRONMENT READY!"
echo "====================================="
echo ""
echo "📋 Available services:"
echo "   🗄️  PostgreSQL: localhost:5432 (testuser/testpass/testdb)"
echo "   🔴 Redis: localhost:6379"
echo "   📦 MinIO: localhost:9000"
echo ""
echo "🐳 Running containers:"
docker ps --format "table {{.Names}}\t{{.Status}}" | grep examify
echo ""
echo "🧪 Run tests with:"
echo "   make test          # Run all tests"
echo "   make test-quick    # Stop on first failure"
echo "   make ci-test       # Run exactly like CI does"
echo ""
echo "🛑 Stop test services with:"
echo "   docker compose -f docker-compose-test.yml down"
echo ""
echo "✅ Examify API is ready for testing!"
