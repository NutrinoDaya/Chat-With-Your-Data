#!/bin/bash
set -e

# Set working directory
cd /app

# Start the FastAPI server with correct module path
echo "Starting API server..."
exec uvicorn src.app.main:app --host 0.0.0.0 --port 8001
