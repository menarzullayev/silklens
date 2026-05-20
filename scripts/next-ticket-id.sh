#!/usr/bin/env bash
# next-ticket-id.sh — emit the next available SILK-NNNN ticket ID.
#
# Scans PROGRESS.md + all docs/*.md + git history for SILK-NNNN matches,
# finds the highest, returns +1 padded to 4 digits. See docs/TRACKING_CONVENTION.md.

set -euo pipefail

repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"

# Search current tree + git history for SILK-NNNN tokens.
# Exclude the convention doc itself — its examples are illustrative, not allocations.
highest=$(
  {
    grep -rhoE 'SILK-[0-9]{4}' \
      --exclude='TRACKING_CONVENTION.md' \
      --exclude='next-ticket-id.sh' \
      PROGRESS.md docs/ services/ apps/ scripts/ 2>/dev/null || true
    git log --all --pretty=format:'%s%n%b' 2>/dev/null | grep -oE 'SILK-[0-9]{4}' || true
  } \
    | sed 's/^SILK-0*//' \
    | sort -n \
    | tail -1
)

next=$(( ${highest:-0} + 1 ))
printf 'SILK-%04d\n' "$next"
