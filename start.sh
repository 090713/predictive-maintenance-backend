#!/bin/bash
# Backend startup script

set -e

echo "=== Predictive Maintenance Backend ==="

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
    echo "Please edit .env with your MongoDB URI"
    exit 1
fi

# Run
PORT=${PORT:-8000}
echo "Starting server on http://localhost:$PORT"
echo "API docs: http://localhost:$PORT/docs"
uvicorn backend.main:app --host 0.0.0.0 --port $PORT
