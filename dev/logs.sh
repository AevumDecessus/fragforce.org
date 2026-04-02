#!/usr/bin/env bash
# Tail logs for a dev stack service.
#
# Usage:
#   dev/logs.sh             # web (default)
#   dev/logs.sh worker
#   dev/logs.sh beat
#   dev/logs.sh db
#   dev/logs.sh redis

cd "$(git rev-parse --show-toplevel)"

SERVICE="${1:-web}"
docker compose logs -f "$SERVICE"
