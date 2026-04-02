#!/usr/bin/env bash
# Run pyflakes across the entire codebase (not just staged files).
# Useful for a full check before opening a PR.
#
# Usage:
#   dev/lint.sh             # lint all Python files
#   dev/lint.sh ffdonations # lint a specific app directory

cd "$(git rev-parse --show-toplevel)"

TARGET="${1:-.}"
FILES=$(find "$TARGET" -name "*.py" | grep -v '\.git' | grep -v migrations | tr '\n' ' ')

if [ -z "$FILES" ]; then
    echo "No Python files found in: $TARGET"
    exit 0
fi

echo "Running pyflakes on $(echo $FILES | wc -w | tr -d ' ') Python files..."
docker compose exec -T web pipenv run python -m pyflakes $FILES
