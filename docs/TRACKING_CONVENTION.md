# SilkLens — Tracking Convention

> **Source of truth:** `PROGRESS.md` (markdown, git-tracked).
> Every new work item gets a `SILK-NNNN` ticket ID. Commits reference the ID.
> Goal: agent-friendly tracking with full git audit trail, no external tools.

---

## Ticket ID format

```
SILK-NNNN
```

- **Prefix:** `SILK` (always uppercase, no hyphens inside)
- **NNNN:** zero-padded 4-digit sequential number, e.g. `SILK-0042`
- **Range:** `SILK-0001` … `SILK-9999`
- **Allocation:** strictly sequential — next ID = highest existing + 1
- **Never reuse:** if a ticket is dropped, its ID is retired (mark `[⏭️] SILK-XXXX DROPPED`)

Use `./scripts/next-ticket-id.sh` to get the next available ID.

---

## Status enum

| Symbol | Meaning | When to use |
|---|---|---|
| `[ ]` | TODO | Backlog — work not started |
| `[🔄]` | IN_PROGRESS | Active — someone is touching it now |
| `[✅]` | DONE | Shipped + verified (tests pass, DB confirms, etc.) |
| `[❌]` | BLOCKED | Cannot proceed (external dependency, decision pending) |
| `[⏭️]` | DEFERRED | Postponed deliberately, not blocked — has a deferred-to milestone |

Exactly one of these must precede every ticket line.

---

## Priority enum

| Emoji | Priority | Definition |
|---|---|---|
| 🔴 | CRITICAL | Blocks release / breaks production / data loss risk |
| 🟡 | HIGH | Important for current FAZA / user-visible feature |
| 🟢 | MEDIUM | Nice to have / polish / refactor |
| ⚪ | LOW | Future / speculative |

Place the emoji immediately after the ticket ID.

---

## Line format

```markdown
- [STATUS] **SILK-NNNN** PRIORITY Short title — body / context / file refs
```

### Examples (use `SILK-NNNN` placeholder — do not write real-looking numbers in docs)

```markdown
- [✅] **SILK-NNNN** 🔴 OTP verify endpoint — `POST /v1/auth/verify-email` + idempotent SqlUserRepository.verify_email()
- [🔄] **SILK-NNNN** 🟡 HeritageDetailPage AR overlay — needs ARCore device test
- [ ] **SILK-NNNN** 🟢 Refactor `dio_client.dart` interceptor order
- [❌] **SILK-NNNN** 🔴 Apple Sign In — BLOCKED on Apple Dev account ($99/yr)
- [⏭️] **SILK-NNNN** ⚪ Real LLaVA inference — DEFERRED to FAZA 8 (GPU SSH access)
```

> Why placeholder: real-looking IDs in docs get picked up by `./scripts/next-ticket-id.sh`
> as "burned" allocations and skipped forever. Always use `SILK-NNNN` in example text.

### File / line refs

Cite source locations inside ticket body using `[file.dart:42](path/to/file.dart#L42)` syntax. Agents and IDEs can navigate directly.

---

## Commit message convention

```
<type>(<scope>): SILK-NNNN[, SILK-NNNN, …] — <subject>

<body>

[Co-Authored-By: …]
```

- **type:** `feat` | `fix` | `refactor` | `docs` | `test` | `chore` | `perf`
- **scope:** area touched (`auth`, `heritage`, `mobile`, `ci`, …)
- **SILK-NNNN:** one or more ticket IDs this commit closes/touches
- **subject:** ≤72 chars, imperative ("add", "fix", "rename")

### Examples

```
feat(auth): SILK-NNNN — OTP verify endpoint + Redis service
fix(mobile): SILK-NNNN, SILK-NNNN — confirm password validator + locale strings
refactor(infra): SILK-NNNN — collapse 3 interceptors into single chain
docs: SILK-NNNN — log Apple Sign In blocker
```

A single commit can close multiple tickets when the work is naturally atomic. Don't pad commits with unrelated IDs.

When closing a ticket via commit: change its status `[ ]` → `[✅]` in the same commit's PROGRESS.md edit.

---

## Sections in PROGRESS.md

Tickets live grouped by **logical area** (not by sprint — solo dev has no sprints). Current section taxonomy:

```
FAZA 1 / 2 / 3 / 4 / 5 / 6-7         — phased milestones (historical + current)
Auth Pipeline (DATE)                  — feature ship sections
Flutter Design System                 — module-specific tracker
Open EPIC-NNN                         — multi-ticket epics still in flight
Open / deferred                       — orphan items waiting for unblocking
```

Within a section, order tickets by **status first** (`[🔄]` before `[ ]` before `[⏭️]` before `[❌]`), then by priority.

---

## What goes into a ticket vs. just a commit

| Worth a ticket | Just a commit (no ticket) |
|---|---|
| User-visible feature | Typo fix |
| API surface change | Test-only refactor |
| New endpoint / page / migration | Comment update |
| Cross-file refactor | Single-file lint cleanup |
| External dependency change | Config bump < 1 line |
| Anything > 1 hour of work | Anything < 15 min and obvious |

**Rule of thumb:** if a change deserves discussion in HANDOFF or future-you would want to know *why*, it gets a ticket.

---

## Closed-item retention

- Closed `[✅]` tickets stay in PROGRESS.md as historical record (do not delete)
- After a FAZA tag (`v0.X.0-beta`) closes, its `[✅]` items can be collapsed into a one-line summary if the section grows past ~50 lines, but the ticket IDs remain searchable via `grep SILK-XXXX` in git history

---

## Retired (burned) ID ranges

The script `./scripts/next-ticket-id.sh` treats any `SILK-NNNN` that ever appeared in working tree or git history as allocated, even if it was only an accidental example.

| Range | Reason | Decision |
|---|---|---|
| `SILK-0021`…`SILK-0042` | Burned by example numeric IDs in early CLAUDE.md / TRACKING_CONVENTION.md commit bodies | RETIRED — never allocate |

**Lesson:** in docs, always write `SILK-NNNN` (literal placeholder), never a real-looking number. The git history is immutable, so a single careless example permanently burns IDs.

---

## Anti-patterns to avoid

- ❌ Reusing a retired SILK ID
- ❌ Creating a ticket for trivial chores (see table above)
- ❌ Status update via commit message only — always update PROGRESS.md too
- ❌ Multi-area "mega-tickets" (e.g. "SILK-0042 — refactor everything") — split into atomic tickets
- ❌ `[✅]` without verifiable proof (test pass / screenshot / DB row / curl)
- ❌ Letting `[🔄]` linger > 7 days without status update (move to `[❌]` BLOCKED if stuck)

---

*Convention v1.0 · Established 2026-05-19 · Owner: project lead*
