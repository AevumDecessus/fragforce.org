#!/usr/bin/env bash
# Regenerate pip-tools lockfiles inside the dev container.
#
# Usage:
#   dev/pip-compile.sh                          # regenerate all three lockfiles
#   dev/pip-compile.sh prod                     # regenerate requirements.txt only
#   dev/pip-compile.sh ci                       # regenerate requirements-ci.txt only
#   dev/pip-compile.sh dev                      # regenerate requirements-dev.txt only
#   dev/pip-compile.sh --upgrade                # regenerate all and allow upgrades
#   dev/pip-compile.sh --upgrade-package <pkg>  # upgrade a single package across all files
#
# pip>=26 is ensured automatically before compiling.

cd "$(git rev-parse --show-toplevel)"

if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker daemon is not running or not accessible." >&2
    exit 1
fi

if ! docker compose ps -q --status running web 2>/dev/null | grep -q .; then
    echo "Containers not running - starting dev stack..."
    dev/start.sh
fi

UPGRADE_FLAG=""
UPGRADE_PACKAGE=""
TARGET="all"

# Ensure pip>=26 - older pip fails on kombu's setup.py (use_2to3 removed in setuptools 58+)
docker compose exec -T web pip install --quiet "pip>=26" 2>/dev/null || true

while [[ $# -gt 0 ]]; do
    case "$1" in
        --upgrade) UPGRADE_FLAG="--upgrade"; shift ;;
        --upgrade-package) UPGRADE_PACKAGE="$2"; shift 2 ;;
        prod|ci|dev) TARGET="$1"; shift ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

if [[ -n "$UPGRADE_PACKAGE" ]]; then
    UPGRADE_OR_NO_UPGRADE="--upgrade-package $UPGRADE_PACKAGE"
else
    UPGRADE_OR_NO_UPGRADE="${UPGRADE_FLAG:---no-upgrade}"
fi

compile_prod() {
    echo "Compiling requirements.txt..."
    docker compose exec -T web pip-compile /code/pyproject.toml \
        -o /code/requirements.txt \
        --generate-hashes \
        $UPGRADE_OR_NO_UPGRADE
}

compile_ci() {
    echo "Compiling requirements-ci.txt..."
    docker compose exec -T web pip-compile /code/pyproject.toml \
        --extra ci \
        -o /code/requirements-ci.txt \
        --generate-hashes \
        $UPGRADE_OR_NO_UPGRADE \
        --allow-unsafe
}

compile_dev() {
    echo "Compiling requirements-dev.txt..."
    docker compose exec -T web pip-compile /code/pyproject.toml \
        --extra dev \
        -o /code/requirements-dev.txt \
        --generate-hashes \
        $UPGRADE_OR_NO_UPGRADE \
        --allow-unsafe
}

case "$TARGET" in
    prod) compile_prod ;;
    ci)   compile_ci ;;
    dev)  compile_dev ;;
    all)
        compile_prod
        compile_ci
        compile_dev
        ;;
esac

echo ""
echo "Done. Review changes then run dev/reset.sh --clean to rebuild containers."
