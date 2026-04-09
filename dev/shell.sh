#!/usr/bin/env bash
# Open a shell inside the web container.
#
# Usage:
#   dev/shell.sh            # bash shell with pipenv activated
#   dev/shell.sh django     # Django manage.py shell
#   dev/shell.sh db         # Django dbshell (postgres)

cd "$(git rev-parse --show-toplevel)"

# Ensure containers are running
if ! docker compose ps -q --status running web 2>/dev/null | grep -q .; then
    echo "Containers not running - starting dev stack..."
    dev/start.sh
fi

case "${1:-bash}" in
    django)
        docker compose exec web pipenv run python manage.py shell
        ;;
    db)
        docker compose exec web pipenv run python manage.py dbshell
        ;;
    bash|"")
        docker compose exec web pipenv shell
        ;;
    *)
        echo "Usage: dev/shell.sh [bash|django|db]"
        exit 1
        ;;
esac
