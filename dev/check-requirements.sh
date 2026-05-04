#!/usr/bin/env bash
# Check for version differences between requirements.txt, requirements-ci.txt,
# and requirements-dev.txt. Packages shared across files should be at the same version.
#
# Usage:
#   dev/check-requirements.sh              # check for diffs, exit 1 if found
#   dev/check-requirements.sh --quiet      # suppress output, only exit code
#   dev/check-requirements.sh --exclusive  # show which packages are exclusive to each file
#                                           # (useful for evaluating Dependabot PRs)

cd "$(git rev-parse --show-toplevel)"

MODE="${1:-}"

python3 - "$MODE" << 'EOF'
import sys
import re

mode = sys.argv[1]

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

if mode == '--exclusive':
    prod_set = set(prod)
    ci_set   = set(ci)
    dev_set  = set(dev)

    dev_only    = sorted(dev_set - prod_set - ci_set)   # dev only
    ci_dev_only = sorted((ci_set & dev_set) - prod_set)  # ci + dev, not prod
    ci_only     = sorted(ci_set - prod_set - dev_set)    # ci only (currently none expected)

    print("Dependabot PR scope guide:")
    print()

    print(f"  All 3 files (prod + ci + dev): everything in requirements.txt")
    print(f"    → {len(prod_set - ci_set - dev_set) + len(prod_set & ci_set) + len(prod_set & dev_set)} packages shared with prod")

    if ci_dev_only:
        print(f"\n  ci + dev only ({len(ci_dev_only)}) - PRs should touch requirements-ci.txt and requirements-dev.txt:")
        for p in ci_dev_only:
            print(f"    {p}=={ci.get(p) or dev.get(p)}")

    if dev_only:
        print(f"\n  dev only ({len(dev_only)}) - PRs should touch requirements-dev.txt only:")
        for p in dev_only:
            print(f"    {p}=={dev[p]}")

    if ci_only:
        print(f"\n  ci only ({len(ci_only)}) - PRs should touch requirements-ci.txt only:")
        for p in ci_only:
            print(f"    {p}=={ci[p]}")

    sys.exit(0)

# Default: check for version skew
all_pkgs = sorted(set(prod) | set(ci) | set(dev))
diffs = []
for pkg in all_pkgs:
    p, c, d = prod.get(pkg), ci.get(pkg), dev.get(pkg)
    present = [v for v in (p, c, d) if v]
    if len(present) >= 2 and len(set(present)) > 1:
        diffs.append((pkg, p or '-', c or '-', d or '-'))

quiet = mode == '--quiet'
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
