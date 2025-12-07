#!/bin/bash

# Resolve the actual directory of the script (follow symlinks)
SCRIPT_DIR="$(dirname "$(readlink -f "$0")")"

# Change to the project directory
cd "$SCRIPT_DIR" || exit 1
echo "Changed dir to $SCRIPT_DIR"

cd "data"
echo "Fetching data..."
git fetch && git pull

cd ..

# Run your command
uv run streamlit run ./main.py

echo "Updating data..."
cd "data"
git add "my_finance_2025.db"
git commit -S -m "auto update"
git push
echo "Finish uploading data..."
