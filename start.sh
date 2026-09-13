#!/bin/bash
# Backend startup script

set -e

echo "=== Fathom Backend Startup ==="

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "Error: python3 not found"
    exit 1
fi

# Create venv if not exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv .venv
fi

# Activate
source .venv/bin/activate

# Install deps
echo "Installing dependencies..."
pip install -q -r requirements.txt

# Check .env
if [ ! -f ".env" ]; then
    echo "Warning: .env not found, copying from .env.example"
    cp .env.example .env
    echo "Please edit .env with your MongoDB URI and JWT secret"
    exit 1
fi

# Run
echo "Starting server on http://localhost:8000"
echo "API docs: http://localhost:8000/docs"
uvicorn backend.main:app --reload --port 8000