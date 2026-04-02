#!/usr/bin/env bash
# Tear down the dev stack (including volumes) and rebuild from scratch.
# Use this when the DB is in a bad state or migrations have diverged.
#
# Usage:
#   dev/reset.sh          # destroy volumes and restart
#   dev/reset.sh --clean  # also remove built images, forcing a full Docker rebuild

cd "$(git rev-parse --show-toplevel)"

CLEAN=false
if [ "${1:-}" = "--clean" ]; then
    CLEAN=true
fi

if [ "$CLEAN" = true ]; then
    echo "This will destroy all local dev data AND remove built Docker images (full rebuild)."
else
    echo "This will destroy all local dev data (postgres volume, redis volume) and restart."
fi
printf "Continue? [y/N] "
read -r CONFIRM
if [ "$CONFIRM" != "y" ] && [ "$CONFIRM" != "Y" ]; then
    echo "Aborted."
    exit 0
fi

echo ""
echo "Tearing down containers and volumes..."
if [ "$CLEAN" = true ]; then
    docker compose down -v --rmi local
else
    docker compose down -v
fi

echo ""
echo "Rebuilding and starting (this may take a few minutes)..."
exec "$(git rev-parse --show-toplevel)/dev/start.sh"
