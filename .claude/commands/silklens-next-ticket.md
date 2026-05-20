---
description: Allocate the next available SILK-NNNN ticket ID and (optionally) draft a PROGRESS.md entry
allowed-tools: Bash
argument-hint: "[priority emoji] [short title — body...]"
---

# /silklens-next-ticket

Allocates the next available `SILK-NNNN` per `docs/TRACKING_CONVENTION.md`.

**Usage:**

- `/silklens-next-ticket` — just print the next ID
- `/silklens-next-ticket 🟡 Add Apple Sign In integration` — print ID + draft a PROGRESS.md line you can paste

`$ARGUMENTS` format: first token is the priority emoji (🔴 / 🟡 / 🟢 / ⚪), rest is the title.

---

```bash
ID=$(./scripts/next-ticket-id.sh)

if [ -z "$1" ]; then
  echo "Next available ID: $ID"
  echo ""
  echo "Run again with title to draft a PROGRESS.md line:"
  echo "  /silklens-next-ticket 🟡 Your title here"
  exit 0
fi

# First arg is priority emoji
PRIORITY="$1"
shift
TITLE="$*"

case "$PRIORITY" in
  🔴|🟡|🟢|⚪) ;;
  *)
    echo "❌ First arg must be a priority emoji: 🔴 (CRITICAL) · 🟡 (HIGH) · 🟢 (MEDIUM) · ⚪ (LOW)"
    echo "   Got: $PRIORITY"
    exit 1
    ;;
esac

echo "📋 Allocated: $ID"
echo ""
echo "PROGRESS.md line to paste:"
echo ""
echo "- [ ] **$ID** $PRIORITY $TITLE"
echo ""
echo "Commit format:"
echo "  feat(<scope>): $ID — <subject>"
echo ""
echo "Remember:"
echo "  • mark [✅] in PROGRESS.md when you close it in the same commit"
echo "  • only mention $ID in commit bodies — do NOT speculate on future IDs"
echo "  • see docs/TRACKING_CONVENTION.md for full spec"
```
