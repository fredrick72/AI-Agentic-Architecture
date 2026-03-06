#!/usr/bin/env bash
set -euo pipefail

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo ""
echo "============================================="
echo " Athena - Database Intelligence"
echo "============================================="
echo ""

# Check Docker
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}ERROR: Docker is not running.${NC}"
    echo "Install Docker Desktop from https://www.docker.com/products/docker-desktop/"
    exit 1
fi
echo -e "${GREEN}[OK]${NC} Docker is running"

# Check docker compose (v2)
if ! docker compose version > /dev/null 2>&1; then
    echo -e "${RED}ERROR: docker compose (v2) not found.${NC}"
    echo "Update Docker Desktop to the latest version."
    exit 1
fi

# Set up .env
if [ ! -f ".env" ]; then
    if [ ! -f ".env.example" ]; then
        echo -e "${RED}ERROR: .env.example not found. Please re-download the package.${NC}"
        exit 1
    fi
    cp .env.example .env
    echo ""
    echo "Your OpenAI API key is required."
    echo "Get one at: https://platform.openai.com/api-keys"
    echo ""
    read -rp " Enter your OpenAI API key (sk-...): " APIKEY
    if [ -z "$APIKEY" ]; then
        echo -e "${RED}ERROR: API key cannot be empty.${NC}"
        exit 1
    fi
    sed -i.bak "s|OPENAI_API_KEY=sk-...|OPENAI_API_KEY=${APIKEY}|" .env && rm -f .env.bak
    echo -e "${GREEN}[OK]${NC} .env configured"
else
    echo -e "${GREEN}[OK]${NC} .env already exists"
fi

# Pull images
echo ""
echo "Pulling Athena images (this may take a few minutes on first run)..."
docker compose pull
echo -e "${GREEN}[OK]${NC} Images ready"

# Start
echo ""
echo "Starting Athena..."
docker compose up -d

echo ""
echo "Waiting for services to initialize..."
sleep 8

echo ""
echo -e "${GREEN}=============================================${NC}"
echo -e "${GREEN} Athena is running!${NC}"
echo -e "${GREEN} Open: http://localhost:8080${NC}"
echo -e "${GREEN}=============================================${NC}"
echo ""
echo "To stop Athena:  docker compose down"
echo "To view logs:    docker compose logs -f"
echo ""

# Open browser (best-effort)
if command -v open &> /dev/null; then
    open "http://localhost:8080"
elif command -v xdg-open &> /dev/null; then
    xdg-open "http://localhost:8080"
fi
