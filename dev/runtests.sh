#!/usr/bin/env bash
# Run the full test suite (or a subset) via Docker and format output as a GitHub comment.
#
# Usage:
#   dev/runtests.sh               # run all tests
#   dev/runtests.sh ffdonations   # run a single app
#   dev/runtests.sh ffdonations.tests.SomeTestClass.test_method

cd "$(git rev-parse --show-toplevel)"

COMMIT=$(git rev-parse --short HEAD)
DATE=$(date +%Y-%m-%d)

# Run tests, capturing all output (Django test runner writes to stderr)
OUTPUT=$(docker compose exec -T web pipenv run python manage.py test "$@" 2>&1)
EXIT_CODE=$?

# Extract summary lines
SUMMARY=$(echo "$OUTPUT" | grep -E '^(Ran [0-9]+ test|OK$|FAILED \()')
RAN_LINE=$(echo "$SUMMARY" | grep '^Ran ')
STATUS_LINE=$(echo "$SUMMARY" | grep -E '^(OK|FAILED)')

# Extract failure details if any
if [ $EXIT_CODE -ne 0 ]; then
    FAILURES=$(echo "$OUTPUT" | grep -E '^(FAIL|ERROR): ' | sed 's/^/- /')
fi

# Build markdown
echo "## Test Run - \`${1:-all}\` @ \`$COMMIT\`"
echo ""
if [ $EXIT_CODE -eq 0 ]; then
    echo "**:white_check_mark: $RAN_LINE** - $DATE"
else
    echo "**:x: $RAN_LINE** - $DATE"
fi
echo ""
echo "\`\`\`"
echo "$RAN_LINE"
echo ""
echo "$STATUS_LINE"
echo "\`\`\`"

if [ $EXIT_CODE -ne 0 ] && [ -n "$FAILURES" ]; then
    echo ""
    echo "### Failures"
    echo "$FAILURES"
    echo ""
    echo "<details><summary>Full output</summary>"
    echo ""
    echo "\`\`\`"
    echo "$OUTPUT" | grep -v '^Loading .env'
    echo "\`\`\`"
    echo ""
    echo "</details>"
fi

exit $EXIT_CODE
