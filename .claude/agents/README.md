# SilkLens project-local subagents

Five specialist agents that carry SilkLens-specific knowledge (architecture, conventions, gotchas) so a Claude session can delegate recurring work without re-explaining context.

| Agent | When to use | Tools |
|---|---|---|
| **[silklens-migration-author](silklens-migration-author.md)** | Adding tables, indexes, RLS policies, triggers — any Alembic schema change | Read, Write, Edit, Bash, Grep, Glob |
| **[silklens-flutter-e2e-tester](silklens-flutter-e2e-tester.md)** | Driving the connected Redmi device through signup / signin / verify flows | Bash, Read, Edit, Grep, Glob |
| **[silklens-otp-debugger](silklens-otp-debugger.md)** | Diagnosing OTP / email pipeline failures across Redis + Resend + Postgres | Read, Bash, Grep, Glob |
| **[silklens-router-author](silklens-router-author.md)** | Adding a new FastAPI endpoint with auth + rate limit + audit + RBAC | Read, Write, Edit, Bash, Grep, Glob |
| **[silklens-flutter-page-author](silklens-flutter-page-author.md)** | Adding a new Flutter screen with Clean Arch + Riverpod + 4-locale i18n | Read, Write, Edit, Bash, Grep, Glob |

These agents complement (do not replace) the 12 global agents in `~/.claude/agents/` (architect, code-reviewer, security-reviewer, …). Global agents are language/framework-agnostic; project-local agents carry the SilkLens domain.

## How to invoke

From within a Claude Code session:

```
Use the silklens-migration-author agent to add a `heritage_audit_log` partitioned table.
```

Or via the `Agent` tool:
```json
{
  "subagent_type": "silklens-migration-author",
  "description": "Add heritage_audit_log table",
  "prompt": "Add a new partitioned table heritage_audit_log mirroring heritage_objects partitioning. ..."
}
```

## Authoring conventions

Each agent file follows the standard format used by global agents:

```yaml
---
name: <slug>
description: <one-line trigger sentence — used by Claude to decide when to spawn>
tools: ["Read", "Write", ...]
model: <sonnet|opus|haiku>
---

## Prompt Defense Baseline
- ...

You are the SilkLens **<role>**. <one-paragraph specialty>.

## Authoritative references
1. CLAUDE.md sections X, Y
2. docs/architecture/...

## Non-negotiable rules
...

## Workflow / Skeleton / Anti-patterns
...

## Output format
...
```

Keep them under ~300 lines. Quality beats quantity — agents should excel at one thing each.

## Adding a new project-local agent

1. Identify a recurring task (≥3 occurrences in last 2 weeks, takes >15 min each time, involves project-specific knowledge)
2. Create `<slug>.md` here following the format above
3. Add a row to the table at the top of this README
4. Test by spawning it on a real task
5. Commit with `feat(agents): SILK-NNNN — add <slug> subagent`

Avoid creating agents for one-off work or for tasks already handled well by global agents.
