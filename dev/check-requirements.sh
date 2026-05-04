#!/usr/bin/env bash
# Check for version differences between requirements.txt, requirements-ci.txt,
# and requirements-dev.txt. Packages shared across files should be at the same version.
#
# Usage:
#   dev/check-requirements.sh          # check for diffs, exit 1 if found
#   dev/check-requirements.sh --quiet  # suppress output, only exit code

cd "$(git rev-parse --show-toplevel)"

QUIET="${1:-}"

python3 - "$QUIET" << 'EOF'
import sys
import re

quiet = sys.argv[1] == '--quiet'

def parse(path):
    versions = {}
    with open(path) as f:
        for line in f:
            line = line.strip().rstrip(' \\')
            m = re.match(r'^([A-Za-z0-9][A-Za-z0-9._-]*)(?:\[.*?\])?==([^\s;]+)', line)
            if m:
                pkg = m.group(1).lower().replace('-', '_').replace('.', '_')
                versions[pkg] = m.group(2)
    return versions

prod = parse('requirements.txt')
ci   = parse('requirements-ci.txt')
dev  = parse('requirements-dev.txt')

all_pkgs = sorted(set(prod) | set(ci) | set(dev))
diffs = []
for pkg in all_pkgs:
    p, c, d = prod.get(pkg), ci.get(pkg), dev.get(pkg)
    present = [v for v in (p, c, d) if v]
    if len(present) >= 2 and len(set(present)) > 1:
        diffs.append((pkg, p or '-', c or '-', d or '-'))

if diffs:
    if not quiet:
        print(f"{'Package':<40}  {'prod':<14}  {'ci':<14}  dev")
        print('-' * 80)
        for pkg, p, c, d in diffs:
            print(f"{pkg:<40}  {p:<14}  {c:<14}  {d}")
        print(f"\n{len(diffs)} package(s) have version differences between lockfiles.")
        print("Run dev/pip-compile.sh to regenerate all three from pyproject.toml.")
    sys.exit(1)
else:
    if not quiet:
        print("All shared packages are at consistent versions across lockfiles.")
    sys.exit(0)
EOF
