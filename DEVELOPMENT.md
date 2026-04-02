# Development Guide

## Requirements

- [Docker](https://docker.com)
- [Docker Compose](https://docs.docker.com/compose/)

## Initial Setup

```bash
cp env.sample .env
# Optionally generate a secret key and set SECRET_KEY in .env
```

Then start the dev stack - on first run this will build the containers, run migrations, load the HC schema, and collect static files:

```bash
dev/start.sh
```

## Dev Scripts

All developer scripts live in `dev/` and can be run from the repo root.

| Script | Description |
|--------|-------------|
| `dev/start.sh` | Start the dev stack. Detects first run and handles setup automatically. |
| `dev/reset.sh` | Tear down volumes and restart. Use `--clean` to also remove built images and force a full Docker rebuild. |
| `dev/shell.sh [bash\|django\|db]` | Open a shell in the web container: bash (default), Django shell, or dbshell. |
| `dev/lint.sh [dir]` | Run pyflakes across all Python files (or a specific app directory). |
| `dev/logs.sh [service]` | Tail logs for a service. Defaults to `web`. |
| `dev/runtests.sh [target]` | Run tests and format output as a GitHub-ready markdown comment. |

## Running Tests

```bash
# Run all tests
dev/runtests.sh

# Run a single app's tests
dev/runtests.sh ffdonations

# Run a specific test class or method
dev/runtests.sh ffdonations.tests.TeamAdminSyncDonationsTest
dev/runtests.sh ffdonations.tests.TeamAdminSyncDonationsTest.test_queues_task_for_each_selected_team
```

Or use Django directly:

```bash
docker compose exec web pipenv run python manage.py test
```

## Useful Commands

Inside the container (`dev/shell.sh`):

```bash
python manage.py shell       # Django shell
python manage.py dbshell     # Postgres shell
python manage.py migrate     # Run migrations
python manage.py collectstatic --no-input
```

## Environment Variables

Copy `env.sample` to `.env` to get started. Key variables:

| Variable | Description |
|----------|-------------|
| `SECRET_KEY` | Django secret key |
| `EXTRALIFE_TEAMID` | Extra Life team ID to sync |
| `TILTIFY_TOKEN` / `TILTIFY_TEAMS` | Tiltify auth and team slugs |
| `FRAG_BOT_API` / `FRAG_BOT_KEY` | Twitch bot integration |
| `REDIS_URL` | Redis connection URL |

See `env.sample` and `fforg/settings.py` for the full list.
