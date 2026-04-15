#!/usr/bin/env bash
# Run the test suite with coverage and report results.
#
# Usage:
#   dev/coverage.sh               # run all tests with coverage
#   dev/coverage.sh ffdonations   # run a single app with coverage

cd "$(git rev-parse --show-toplevel)"

# Check Docker daemon is available before proceeding
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker daemon is not running or not accessible." >&2
    exit 1
fi

# Ensure containers are running
if ! docker compose ps -q --status running web 2>/dev/null | grep -q .; then
    echo "Containers not running - starting dev stack..."
    dev/start.sh
fi

COMMIT=$(git rev-parse --short HEAD)
DATE=$(date +%Y-%m-%d)
FENCE='```'

# Run tests with coverage, capturing all output
OUTPUT=$(docker compose exec -T web pipenv run coverage run manage.py test "$@" 2>&1)
EXIT_CODE=$?

# Extract test summary
SUMMARY=$(echo "$OUTPUT" | grep -E '^(Ran [0-9]+ test|OK$|FAILED \()')
RAN_LINE=$(echo "$SUMMARY" | grep '^Ran ')
STATUS_LINE=$(echo "$SUMMARY" | grep -E '^(OK|FAILED)')

# Extract failure details if any
if [[ $EXIT_CODE -ne 0 ]]; then
    FAILURES=$(echo "$OUTPUT" | grep -E '^(FAIL|ERROR): ' | sed 's/^/- /')
fi

# Generate coverage report, sorted by coverage % ascending (worst first)
RAW_COVERAGE=$(docker compose exec -T web pipenv run coverage report --skip-covered 2>&1)
HEADER=$(echo "$RAW_COVERAGE" | grep -E '^(Loading|Name|---)')
TOTAL_LINE=$(echo "$RAW_COVERAGE" | grep '^TOTAL')
SEPARATOR=$(echo "$RAW_COVERAGE" | grep '^---' | head -1)
SORTED=$(echo "$RAW_COVERAGE" | grep -v -E '^(Loading|Name|---|TOTAL)' | grep '%' \
    | awk '{pct=$NF; gsub(/%/,"",pct); print pct"\t"$0}' | sort -n | cut -f2-)
COVERAGE=$(printf '%s\n%s\n%s\n%s' "$HEADER" "$SORTED" "$SEPARATOR" "$TOTAL_LINE")
TOTAL=$(echo "$TOTAL_LINE" | awk '{print $NF}')

# Build markdown
echo "## Coverage Run - \`${1:-all}\` @ \`$COMMIT\`"
echo ""
if [[ $EXIT_CODE -eq 0 ]]; then
    echo "**:white_check_mark: $RAN_LINE** - $DATE"
else
    echo "**:x: $RAN_LINE** - $DATE"
fi
echo ""
echo "**Total coverage: ${TOTAL:-unknown}**"
echo ""
echo "$FENCE"
echo "$RAN_LINE"
echo ""
echo "$STATUS_LINE"
echo "$FENCE"

if [[ $EXIT_CODE -ne 0 && -n "$FAILURES" ]]; then
    echo ""
    echo "### Failures"
    echo "$FAILURES"
fi

echo ""
echo "### Coverage Report (files below 100%)"
echo ""
echo "$FENCE"
echo "$COVERAGE"
echo "$FENCE"

exit $EXIT_CODE
