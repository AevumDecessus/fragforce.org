#!/usr/bin/env bash
# Push the current branch, run the test suite, and open a PR with test results in the body.
#
# Usage:
#   dev/pr.sh "PR title"
#   dev/pr.sh "PR title" --base some-branch   # default base is dev

cd "$(git rev-parse --show-toplevel)"

TITLE="${1}"
if [ -z "$TITLE" ]; then
    echo "Usage: dev/pr.sh \"PR title\" [--base <branch>]"
    exit 1
fi
shift

BASE="dev"
while [ $# -gt 0 ]; do
    case "$1" in
        --base) BASE="$2"; shift 2 ;;
        *) echo "Unknown argument: $1"; exit 1 ;;
    esac
done

BRANCH=$(git rev-parse --abbrev-ref HEAD)

echo "Pushing $BRANCH to origin..."
git push -u origin "$BRANCH"

echo ""
echo "Running tests..."
TEST_OUTPUT=$(dev/runtests.sh 2>/dev/null)

echo ""
echo "Creating PR..."
gh pr create \
    --title "$TITLE" \
    --base "$BASE" \
    --body "$(cat <<EOF
## Test Results

$TEST_OUTPUT
EOF
)" "$@"
