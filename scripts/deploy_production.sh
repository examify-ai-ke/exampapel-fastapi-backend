#!/bin/bash
###############################################################################
# Production Deployment Script
# This script automates the deployment of the Examify backend to production
###############################################################################

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Examify Production Deployment${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""

# Check if we're in the correct directory
if [ ! -f "docker-compose.prod.yml" ]; then
    echo -e "${RED}Error: docker-compose.prod.yml not found!${NC}"
    echo "Please run this script from the project root directory."
    exit 1
fi

# Check if .env.production exists
if [ ! -f ".env.production" ]; then
    echo -e "${YELLOW}Warning: .env.production not found!${NC}"
    echo "Creating from template..."
    if [ -f ".env.production.example" ]; then
        cp .env.production.example .env.production
        echo -e "${YELLOW}Please edit .env.production with your production values before continuing.${NC}"
        read -p "Press enter when ready to continue..."
    else
        echo -e "${RED}Error: .env.production.example not found!${NC}"
        exit 1
    fi
fi

# Check if backup file exists
if [ ! -f "exams_fastapi_db_clean_backup.dump" ]; then
    echo -e "${YELLOW}Warning: Database backup file not found!${NC}"
    echo "Database will start empty (unless data already exists)"
    echo ""
fi

echo -e "${GREEN}Step 1: Pulling latest images...${NC}"
docker-compose -f docker-compose.prod.yml pull

echo ""
echo -e "${GREEN}Step 2: Building custom images...${NC}"
docker-compose -f docker-compose.prod.yml build --no-cache

echo ""
echo -e "${GREEN}Step 3: Stopping existing containers...${NC}"
docker-compose -f docker-compose.prod.yml down

echo ""
echo -e "${GREEN}Step 4: Starting services...${NC}"
docker-compose -f docker-compose.prod.yml --env-file .env.production up -d

echo ""
echo -e "${GREEN}Step 5: Waiting for services to be healthy...${NC}"
sleep 10

# Check service health
echo "Checking service health..."
docker-compose -f docker-compose.prod.yml ps

echo ""
echo -e "${GREEN}Step 6: Checking database initialization...${NC}"
docker-compose -f docker-compose.prod.yml logs examify_backend_prod | grep -i "initialization\|backup\|database" | tail -20

echo ""
echo -e "${GREEN}Step 7: Running health checks...${NC}"

# Wait a bit more for backend to fully start
sleep 5

# Check if backend is responding
if docker exec examify_backend_prod curl -f http://localhost:8000/api/v1/health > /dev/null 2>&1; then
    echo -e "${GREEN}✓ Backend health check passed${NC}"
else
    echo -e "${RED}✗ Backend health check failed${NC}"
    echo "Check logs with: docker-compose -f docker-compose.prod.yml logs examify_backend_prod"
fi

echo ""
echo -e "${GREEN}================================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}================================================${NC}"
echo ""
echo "Services status:"
docker-compose -f docker-compose.prod.yml ps
echo ""
echo "Useful commands:"
echo "  View logs: docker-compose -f docker-compose.prod.yml logs -f"
echo "  Stop services: docker-compose -f docker-compose.prod.yml down"
echo "  Restart: docker-compose -f docker-compose.prod.yml restart"
echo "  View specific service logs: docker-compose -f docker-compose.prod.yml logs -f examify_backend_prod"
echo ""
echo "API should be available at: https://api.exampapel.com"
echo "(Make sure DNS is pointing to this server)"
echo ""

# Show backend logs for any errors
echo -e "${YELLOW}Recent backend logs:${NC}"
docker-compose -f docker-compose.prod.yml logs --tail=30 examify_backend_prod
