#!/usr/bin/env bash
# Start the full dev stack.
# On first run (no built image), builds containers and runs first-time setup.
# On subsequent runs, just starts containers and waits for readiness.

cd "$(git rev-parse --show-toplevel)"

if [[ ! -f .env ]]; then
    echo "Error: .env file not found."
    echo "Run: cp env.sample .env"
    exit 1
fi

FIRST_RUN=false
if ! docker image inspect fragforceorg-web &>/dev/null; then
    FIRST_RUN=true
fi

if [[ "$FIRST_RUN" = true ]]; then
    echo "First run detected — building containers (this will take a few minutes)..."
    docker compose up --build -d
    echo ""
    echo "Waiting for migrations to finish..."
    docker compose wait init
    echo ""
    echo "Running collectstatic..."
    docker compose exec -T web pipenv run python manage.py collectstatic --no-input
else
    docker compose up -d
fi

echo ""
echo "Installing dev dependencies (pyflakes, etc.)..."
docker compose exec -T web pipenv install --dev

echo ""
echo "Waiting for web server at http://localhost:8000/ ..."
for i in $(seq 1 30); do
    if curl -sf http://localhost:8000/ >/dev/null 2>&1; then
        break
    fi
    sleep 2
done

echo ""
echo "Dev server ready: http://localhost:8000/"
echo ""
docker compose ps
