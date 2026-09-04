#!/bin/bash
# VERIFY-X 2.0 — Setup Script
set -e

echo "═══════════════════════════════════════════"
echo "  VERIFY-X 2.0 — Setup"
echo "═══════════════════════════════════════════"

# Check prerequisites
command -v python3 >/dev/null 2>&1 || { echo "Python 3.11+ required"; exit 1; }
command -v node >/dev/null 2>&1 || { echo "Node.js 20+ required"; exit 1; }
command -v docker >/dev/null 2>&1 || { echo "Docker required"; exit 1; }

# Copy environment file
if [ ! -f .env ]; then
    cp .env.example .env
    echo "✓ Created .env from .env.example"
fi

# Backend setup
echo ""
echo "Setting up backend..."
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cd ..
echo "✓ Backend dependencies installed"

# Frontend setup
echo ""
echo "Setting up frontend..."
cd frontend
npm install
cd ..
echo "✓ Frontend dependencies installed"

# Start infrastructure
echo ""
echo "Starting PostgreSQL and Redis..."
docker-compose up -d postgres redis
echo "✓ Infrastructure started"

echo ""
echo "═══════════════════════════════════════════"
echo "  Setup complete!"
echo ""
echo "  Start backend:  cd backend && uvicorn app.main:app --reload"
echo "  Start frontend: cd frontend && npm run dev"
echo "═══════════════════════════════════════════"
