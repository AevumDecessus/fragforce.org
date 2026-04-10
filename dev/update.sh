#!/usr/bin/env bash
# Pull the latest changes and update the dev environment.
# Rebuilds the Docker image if Pipfile.lock changed, then runs migrations.
#
# Usage:
#   dev/update.sh

cd "$(git rev-parse --show-toplevel)"

# Ensure containers are running
if ! docker compose ps -q --status running web 2>/dev/null | grep -q .; then
    echo "Containers not running - starting dev stack..."
    dev/start.sh
    exit $?
fi

# Track whether Pipfile.lock changes after the pull
LOCKFILE_BEFORE=$(git rev-parse HEAD:Pipfile.lock 2>/dev/null)

echo "Pulling latest changes..."
git pull --ff-only

LOCKFILE_AFTER=$(git rev-parse HEAD:Pipfile.lock 2>/dev/null)

if [[ "$LOCKFILE_BEFORE" != "$LOCKFILE_AFTER" ]]; then
    echo ""
    echo "Pipfile.lock changed - rebuilding image..."
    docker compose build web
    docker compose up -d web
fi

echo ""
echo "Running migrations..."
dev/migrate.sh
