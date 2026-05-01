#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# AgroVault — Production Docker deployment
# Usage: bash scripts/deploy.sh [--rebuild]
# ─────────────────────────────────────────────────────────────────────────────

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

GREEN='\033[0;32m'; YELLOW='\033[1;33m'; RED='\033[0;31m'; NC='\033[0m'

REBUILD=false
for arg in "$@"; do [ "$arg" = "--rebuild" ] && REBUILD=true; done

echo -e "${GREEN}AgroVault — Docker Deploy${NC}"

# Check .env exists
if [ ! -f ".env" ]; then
    echo -e "${RED}✗ .env not found. Copy .env.example → .env and set your SECRET_KEY.${NC}"
    exit 1
fi

# Warn if SECRET_KEY is still the default
if grep -q "REPLACE_WITH_64_CHAR" .env; then
    echo -e "${RED}✗ You must set a real SECRET_KEY in .env before deploying!${NC}"
    exit 1
fi

echo -e "${GREEN}[1/3] Pulling latest changes...${NC}"
git pull --ff-only 2>/dev/null || echo "  (not a git repo or already up to date)"

if [ "$REBUILD" = true ]; then
    echo -e "${GREEN}[2/3] Rebuilding Docker images (--rebuild flag set)...${NC}"
    docker compose build --no-cache
else
    echo -e "${GREEN}[2/3] Building Docker images (incremental)...${NC}"
    docker compose build
fi

echo -e "${GREEN}[3/3] Starting containers...${NC}"
docker compose up -d

echo ""
echo -e "${GREEN}✓ AgroVault is running!${NC}"
echo -e "  App:    http://localhost:80"
echo -e "  Health: http://localhost:80/health"
echo ""
echo -e "  Logs:   docker compose logs -f"
echo -e "  Stop:   docker compose down"
