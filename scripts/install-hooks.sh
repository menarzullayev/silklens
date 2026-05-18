#!/usr/bin/env bash
# Install SilkLens git hooks. Run once after cloning:
#   bash scripts/install-hooks.sh
set -euo pipefail
REPO_ROOT="$(git rev-parse --show-toplevel)"
HOOKS_DIR="$REPO_ROOT/.git/hooks"
SCRIPTS_DIR="$REPO_ROOT/scripts/hooks"
echo "Installing git hooks from $SCRIPTS_DIR → $HOOKS_DIR"
for hook in "$SCRIPTS_DIR"/*; do
    name="$(basename "$hook")"
    dest="$HOOKS_DIR/$name"
    cp "$hook" "$dest"
    chmod +x "$dest"
    echo "  ✓ $name"
done
echo "Done. Hooks are active for this clone."
