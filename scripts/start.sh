#!/bin/bash
# ─────────────────────────────────────────────────────────────────────────────
# AgroVault — Local development startup script
# Usage: bash scripts/start.sh
# Starts backend (FastAPI) and frontend (Vite) in parallel.
# ─────────────────────────────────────────────────────────────────────────────

set -e

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BACKEND="$ROOT/backend"
FRONTEND="$ROOT/frontend"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
RED='\033[0;31m'
NC='\033[0m'

echo -e "${CYAN}"
echo "  ┌─────────────────────────────────────┐"
echo "  │     AgroVault — Trade OS  v1.0      │"
echo "  │     Starting development server     │"
echo "  └─────────────────────────────────────┘"
echo -e "${NC}"

# ── Check prerequisites ───────────────────────────────────────────────────────
check_cmd() {
    if ! command -v "$1" &>/dev/null; then
        echo -e "${RED}✗ Required: '$1' not found. Please install it.${NC}"
        exit 1
    fi
}
check_cmd python3
check_cmd node
check_cmd npm

# ── Setup .env ────────────────────────────────────────────────────────────────
if [ ! -f "$ROOT/.env" ]; then
    echo -e "${YELLOW}⚠ No .env found — copying from .env.example${NC}"
    cp "$ROOT/.env.example" "$ROOT/.env"
    echo -e "${YELLOW}  Edit .env and set SECRET_KEY before deploying to production.${NC}"
fi

# ── Backend setup ─────────────────────────────────────────────────────────────
echo -e "\n${GREEN}[1/4] Installing Python dependencies...${NC}"
cd "$BACKEND"
pip install -r requirements.txt --break-system-packages -q 2>&1 | grep -v "^$" || true

echo -e "${GREEN}[2/4] Initialising database...${NC}"
python -c "
from db.session import Base, engine
from models.models import *
Base.metadata.create_all(bind=engine)
print('  ✓ Tables ready')
"

# Seed only if DB is empty
python -c "
from db.session import SessionLocal
from models.models import User
db = SessionLocal()
count = db.query(User).count()
db.close()
if count == 0:
    import subprocess
    r = subprocess.run(['python', 'seed.py'], capture_output=True, text=True)
    print(r.stdout.strip())
else:
    print(f'  ✓ DB already seeded ({count} users)')
"

# ── Frontend setup ────────────────────────────────────────────────────────────
echo -e "${GREEN}[3/4] Installing Node dependencies...${NC}"
cd "$FRONTEND"
npm install --legacy-peer-deps -q 2>&1 | tail -2

# ── Launch both services ──────────────────────────────────────────────────────
echo -e "${GREEN}[4/4] Launching services...${NC}\n"

# Start backend in background
cd "$BACKEND"
uvicorn main:app --host 0.0.0.0 --port 8000 --reload --log-level warning &
BACKEND_PID=$!
echo -e "  ${GREEN}✓ Backend${NC}  → http://localhost:8000/api/health  (PID $BACKEND_PID)"

# Wait for backend to be ready
sleep 2

# Start frontend dev server in background
cd "$FRONTEND"
npm run dev -- --host 0.0.0.0 &
FRONTEND_PID=$!
echo -e "  ${GREEN}✓ Frontend${NC} → http://localhost:5173            (PID $FRONTEND_PID)"

echo ""
echo -e "${CYAN}  Demo accounts:${NC}"
echo -e "  CEO:        ceo@agrovault.com        / demo123"
echo -e "  Director:   director@agrovault.com   / demo123"
echo -e "  Manager:    manager@agrovault.com    / demo123"
echo -e "  Accountant: accountant@agrovault.com / demo123"
echo -e "  Operator:   operator@agrovault.com   / demo123"
echo ""
echo -e "${YELLOW}  Press Ctrl+C to stop both services${NC}"
echo ""

# Trap Ctrl+C and kill both processes
cleanup() {
    echo -e "\n${YELLOW}Shutting down...${NC}"
    kill $BACKEND_PID $FRONTEND_PID 2>/dev/null || true
    echo "Done."
}
trap cleanup INT TERM

# Wait for either process to exit
wait $BACKEND_PID $FRONTEND_PID
