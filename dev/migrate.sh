#!/usr/bin/env bash
# Run Django migrations inside the web container.
#
# Usage:
#   dev/migrate.sh              # run all pending migrations
#   dev/migrate.sh ffdonations  # migrate a specific app

cd "$(git rev-parse --show-toplevel)"

# Ensure containers are running
if ! docker compose ps -q --status running web 2>/dev/null | grep -q .; then
    echo "Containers not running - starting dev stack..."
    dev/start.sh
fi

docker compose exec -T web pipenv run python manage.py migrate "$@"
