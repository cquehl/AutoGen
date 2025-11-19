#!/bin/bash
# Simple script to run the Yamazaki V2 CLI

cd "$(dirname "$0")"

# Use python3 from PATH or virtual environment if activated
if [ -n "$VIRTUAL_ENV" ]; then
    # Use activated virtual environment
    python -m v2.cli
elif [ -f ".venv/bin/python" ]; then
    # Use local .venv if it exists
    .venv/bin/python -m v2.cli
else
    # Fall back to system python3
    python3 -m v2.cli
fi
