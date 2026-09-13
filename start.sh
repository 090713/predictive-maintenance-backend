#!/bin/bash

set -e

echo "=== Predictive Maintenance Backend ==="

PORT=${PORT:-8000}

echo "Starting server on port $PORT"

uvicorn backend.main:app --host 0.0.0.0 --port $PORT