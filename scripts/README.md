# SilkLens scripts

Developer-facing scripts. Everything here is shell or Python and must run on a stock Linux dev box without extra dependencies beyond the project's `.venv`.

| Path | Purpose |
|---|---|
| [`next-ticket-id.sh`](next-ticket-id.sh) | Emit the next available `SILK-NNNN` ticket ID. Scans working tree + git history, returns highest+1 (skipping retired ranges by design). |
| [`install-hooks.sh`](install-hooks.sh) | Install `pre-push` git hook (ruff + pytest). Run once per clone. |
| [`hooks/pre-push`](hooks/pre-push) | Git pre-push: runs ruff lint + pytest. Bypass with `--no-verify` only in emergency. |
| [`hooks/claude-validate-commit-message.sh`](hooks/claude-validate-commit-message.sh) | Claude Code PostToolUse hook. Warns (non-blocking) when a `git commit` subject lacks a SILK-NNNN reference. Configured in `.claude/settings.json`. |

---

## Conventions for new scripts

- Bash scripts use `#!/usr/bin/env bash` + `set -euo pipefail`
- Python scripts run under the project `.venv`; no global dependencies
- Pure-shell scripts must work on Linux; macOS compat is bonus, not required
- All scripts must be idempotent — running twice = same result as running once
- Output: human-readable to stderr, machine-parseable to stdout (one thing per line)
- Document in this README + the script's own header comment

---

## Anti-patterns

- ❌ Scripts that mutate the database without a backup (use Alembic migrations)
- ❌ Scripts that download from network without checksums
- ❌ Scripts with hardcoded paths outside `$repo_root` (use `git rev-parse --show-toplevel`)
- ❌ Scripts that source `.env` (use settings via `make api-*`)
- ❌ Scripts that need sudo (a dev-laptop tool shouldn't)
