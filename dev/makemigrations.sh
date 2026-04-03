#!/usr/bin/env bash
# Create new Django migrations inside the web container.
#
# Usage:
#   dev/makemigrations.sh              # detect changes across all apps
#   dev/makemigrations.sh ffdonations  # create migrations for a specific app

cd "$(git rev-parse --show-toplevel)"

# Ensure containers are running
if ! docker compose ps -q --status running web 2>/dev/null | grep -q .; then
    echo "Containers not running - starting dev stack..."
    dev/start.sh
fi

docker compose exec -T web pipenv run python manage.py makemigrations "$@"
