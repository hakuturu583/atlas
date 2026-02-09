#!/bin/bash
# ATLAS - Startup script

echo "🚀 Starting ATLAS..."

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "❌ uv is not installed. Please install it first:"
    echo "   curl -LsSf https://astral.sh/uv/install.sh | sh"
    exit 1
fi

# Install dependencies
echo "📦 Installing dependencies..."
uv sync

# Run the application
echo "✨ Launching ATLAS on http://localhost:8000"
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
