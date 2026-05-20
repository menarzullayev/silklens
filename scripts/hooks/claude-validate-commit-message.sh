#!/usr/bin/env bash
# claude-validate-commit-message.sh
#
# PostToolUse hook for Bash. When Claude Code runs a `git commit` command,
# this script reads the resulting commit message from the just-created commit
# and checks that the subject line references at least one SILK-NNNN ticket
# OR is a trivial commit type that doesn't require one (per the convention).
#
# Hook contract (Claude Code): we receive the tool input + output via stdin
# as JSON, and the script may exit non-zero to surface a warning. We never
# block the commit — git already happened — but we WARN so future agents
# fix the convention violation.
#
# See docs/TRACKING_CONVENTION.md.

set -euo pipefail

# Read stdin (JSON payload from Claude Code) — we only need the command text
payload=$(cat || true)

# Only act on git-commit invocations
if ! echo "$payload" | grep -qE '"git commit|git[[:space:]]+commit'; then
  exit 0
fi

# Read the most recent commit subject from git
repo_root="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
cd "$repo_root"
subject=$(git log -1 --pretty=format:'%s' 2>/dev/null || echo "")

# If the subject is empty, the commit hasn't landed yet (e.g. failed hook). Bail.
[ -z "$subject" ] && exit 0

# Trivial types that don't require a SILK ID per convention
if echo "$subject" | grep -qE '^(chore|docs|test|style)\(?[a-z-]*\)?:\s+(typo|format|lint|rename|move|comment|cleanup|whitespace)'; then
  exit 0
fi

# Validate: subject mentions SILK-NNNN
if echo "$subject" | grep -qE 'SILK-[0-9]{4}'; then
  exit 0
fi

# Warn (non-blocking) — output goes to Claude Code's tool result transcript
{
  echo ""
  echo "⚠️  Commit subject lacks a SILK-NNNN ticket reference."
  echo "    Subject: \"$subject\""
  echo "    See docs/TRACKING_CONVENTION.md — every non-trivial commit should"
  echo "    reference a ticket: 'feat(scope): SILK-NNNN — description'."
  echo "    Next ID: $(./scripts/next-ticket-id.sh 2>/dev/null || echo 'SILK-NNNN')"
} >&2

# Exit 0 so the commit isn't reverted — we only warn.
exit 0
