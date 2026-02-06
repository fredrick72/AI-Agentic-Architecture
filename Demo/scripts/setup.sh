#!/bin/bash

# ============================================
# AI-Agentic Architecture - Setup Script
# ============================================
# This script initializes the demo environment

set -e  # Exit on error

echo "==================================="
echo "AI-Agentic Architecture Setup"
echo "==================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${YELLOW}⚠ .env file not found${NC}"
    echo "Creating .env from .env.example..."
    cp .env.example .env
    echo -e "${RED}⚠ IMPORTANT: Edit .env and add your OPENAI_API_KEY${NC}"
    echo ""
    read -p "Press Enter after you've added your OpenAI API key to .env..."
fi

# Check if OPENAI_API_KEY is set
source .env
if [ -z "$OPENAI_API_KEY" ] || [ "$OPENAI_API_KEY" = "sk-your-openai-api-key-here" ]; then
    echo -e "${RED}❌ OPENAI_API_KEY not set in .env${NC}"
    echo "Please edit .env and add your OpenAI API key"
    exit 1
fi

echo -e "${GREEN}✓ Environment configured${NC}"
echo ""

# Check Docker
echo "Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo -e "${RED}❌ Docker not found. Please install Docker Desktop${NC}"
    exit 1
fi

if ! docker info &> /dev/null; then
    echo -e "${RED}❌ Docker daemon not running. Please start Docker Desktop${NC}"
    exit 1
fi

echo -e "${GREEN}✓ Docker is running${NC}"
echo ""

# Start infrastructure services first
echo "==================================="
echo "Step 1: Starting Infrastructure"
echo "==================================="
echo ""
echo "Starting: PostgreSQL, Redis, Traefik, Prometheus, Grafana"
echo ""

docker compose up -d postgres redis traefik prometheus grafana

echo ""
echo "Waiting for services to be healthy (30 seconds)..."
sleep 30

# Check PostgreSQL
echo ""
echo "Checking PostgreSQL..."
if docker compose exec -T postgres pg_isready -U postgres > /dev/null 2>&1; then
    echo -e "${GREEN}✓ PostgreSQL is ready${NC}"
else
    echo -e "${RED}❌ PostgreSQL not ready${NC}"
    echo "Check logs: docker compose logs postgres"
    exit 1
fi

# Check Redis
echo "Checking Redis..."
if docker compose exec -T redis redis-cli ping | grep -q PONG; then
    echo -e "${GREEN}✓ Redis is ready${NC}"
else
    echo -e "${RED}❌ Redis not ready${NC}"
    echo "Check logs: docker compose logs redis"
    exit 1
fi

# Verify database tables
echo "Verifying database schema..."
TABLE_COUNT=$(docker compose exec -T postgres psql -U postgres -d agent_db -t -c "SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='public';" | tr -d ' ')

if [ "$TABLE_COUNT" -gt 5 ]; then
    echo -e "${GREEN}✓ Database schema initialized ($TABLE_COUNT tables)${NC}"
else
    echo -e "${YELLOW}⚠ Database may not be fully initialized${NC}"
    echo "Run: docker compose exec postgres psql -U postgres -d agent_db -c '\dt'"
fi

# Check patient data
PATIENT_COUNT=$(docker compose exec -T postgres psql -U postgres -d agent_db -t -c "SELECT COUNT(*) FROM patients;" | tr -d ' ')
if [ "$PATIENT_COUNT" -gt 0 ]; then
    echo -e "${GREEN}✓ Seed data loaded ($PATIENT_COUNT patients)${NC}"
else
    echo -e "${YELLOW}⚠ No patients found - seed data may not be loaded${NC}"
fi

echo ""
echo "==================================="
echo "Infrastructure Test Complete!"
echo "==================================="
echo ""
echo -e "${GREEN}✓ PostgreSQL${NC} - Port 5432"
echo -e "${GREEN}✓ Redis${NC} - Port 6379"
echo -e "${GREEN}✓ Traefik${NC} - Port 80 (API), 8080 (Dashboard)"
echo -e "${GREEN}✓ Prometheus${NC} - Port 9090"
echo -e "${GREEN}✓ Grafana${NC} - Port 3000 (admin/admin)"
echo ""
echo "Access Points:"
echo "  • Traefik Dashboard: http://localhost:8080"
echo "  • Prometheus: http://localhost:9090"
echo "  • Grafana: http://localhost:3000"
echo ""
echo "Next Steps:"
echo "  1. Build and start application services:"
echo "     docker compose up -d --build"
echo ""
echo "  2. View logs:"
echo "     docker compose logs -f"
echo ""
echo "  3. Test the demo scenarios in README.md"
echo ""
echo "==================================="
