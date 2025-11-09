#!/bin/bash

# Resolve the actual directory of the script (follow symlinks)
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

# Change to the project directory
cd "$SCRIPT_DIR" || exit 1
echo "Changed dir to $SCRIPT_DIR"

# Run your command
uv run streamlit run ./main.py
