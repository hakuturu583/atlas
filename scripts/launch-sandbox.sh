#!/bin/bash
# Wrapper script for launch_sandbox.py with virtual environment activation

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

# Activate virtual environment
VENV_PATH="$PROJECT_ROOT/.venv"

if [ ! -d "$VENV_PATH" ]; then
    echo "Error: Virtual environment not found at $VENV_PATH"
    echo "Please run: uv sync"
    exit 1
fi

# Activate venv and run Python script
source "$VENV_PATH/bin/activate"

# Execute Python script with all arguments
python "$SCRIPT_DIR/launch_sandbox.py" "$@"
