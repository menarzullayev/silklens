# mypy --strict Error Categories — SilkLens Backend
> **Generated:** 2026-05-23 · **Total errors:** 381 across 83 files

---

## Top 5 Error Categories

| Error code | Count | Severity | Fix complexity |
|---|---|---|---|
| `[type-arg]` | 109 | 🟡 Low | Easy — add `[str, Any]` to bare `dict`/`list` |
| `[attr-defined]` | 71 | 🔴 High | Medium — real bug indicator, cast or refactor |
| `[unused-ignore]` | 54 | 🟢 Trivial | Easy — delete dead comment |
| `[union-attr]` | 49 | 🔴 High | Medium — null guards missing (REAL BUGS) |
| `[no-any-return]` | 26 | 🟠 Medium | Easy — wrap in `cast()` or constructor |
| `[index]` | 24 | 🔴 High | Medium — indexing into Any/Optional |
| `[no-untyped-call]` | 12 | 🟠 Medium | Add stubs or `# type: ignore[no-untyped-call]` |
| `[arg-type]` | 10 | 🟠 Medium | Real type mismatch — fix call site |
| `[call-arg]` | 9 | 🟠 Medium | Wrong kwargs or missing positional |
| `[call-overload]` | 7 | 🟡 Low | Pick correct overload signature |
| `[untyped-decorator]` | 5 | 🟢 Trivial | Celery decorators — add ignore comment |
| `[assignment]` | 5 | 🟠 Medium | Type mismatch in assignment |
| Other | 4 | varies | — |

---

## 🔴 Highest-risk categories (real bugs)

### `[union-attr]` — 49 errors
**What it means:** Accessing `.attribute` on something that might be `None`.

**Real bug example:**
```python
row = await session.execute(...).fetchone()  # may return None
return row.id  # ❌ CRASHES if row is None
```

**SilkLens impact:** Any of these can cause 500 errors in production for empty DB queries. **Must fix all 49.**

---

### `[attr-defined]` — 71 errors
**What it means:** Accessing attribute that mypy can't prove exists on the type.

**Real bug example:**
```python
result: dict = await api_client.call()
return result.user_id  # ❌ dicts use [] not .
```

**SilkLens impact:** Common in DTO mapping. Real bugs when JSON shape differs from expected.

---

### `[index]` — 24 errors
**What it means:** Subscripting into something that doesn't support it (None, Optional, Any).

**Real bug example:**
```python
data = response.get('items')  # Optional[list]
return data[0]  # ❌ crashes if items missing
```

**SilkLens impact:** Pagination edge cases, missing OpenAPI fields.

---

## 🟢 Easy wins (just cleanup)

### `[unused-ignore]` — 54 errors
54 stale `# type: ignore` comments to delete. Zero risk, just hygiene.

### `[type-arg]` — 109 errors
Add `[str, Any]` etc. to bare generic types. Mechanical fix.

### `[untyped-decorator]` — 5 errors
All on Celery `@shared_task` decorators. Add `# type: ignore[misc]` on the line.

---

## Files by error count (top 25)

| File | Errors |
|---|---|
| `src/api/routers/reseller.py` | 21 |
| `src/api/routers/review_analysis.py` | 20 |
| `src/api/routers/kids_mode.py` | 18 |
| `src/infrastructure/billing/repository.py` | 17 |
| `src/api/routers/photo_guide.py` | 17 |
| `src/infrastructure/notifications/fcm_client.py` | 15 |
| `src/api/routers/expenses.py` | 15 |
| `src/api/routers/memory_book.py` | 13 |
| `src/api/routers/auth.py` | 13 |
| `src/api/routers/trips.py` | 12 |
| `src/infrastructure/mfa/webauthn.py` | 10 |
| `src/api/routers/media.py` | 10 |
| `src/api/routers/heritage.py` | 9 |
| `src/infrastructure/notifications/repository.py` | 8 |
| `src/domain/compliance/service.py` | 8 |
| `src/api/routers/notifications.py` | 8 |
| `src/api/routers/gamification.py` | 8 |
| `src/api/routers/ai.py` | 7 |
| `src/infrastructure/billing/stripe_provider.py` | 6 |
| `src/domain/partnership/service.py` | 6 |
| `src/domain/mfa/service.py` | 6 |
| `src/infrastructure/identity/repositories.py` | 5 |
| `src/domain/media/service.py` | 5 |
| `src/domain/finetuning/service.py` | 5 |
| `src/api/routers/social.py` | 5 |

---

## Initial 3 fixes (already applied)

| File | Fix |
|---|---|
| `src/domain/identity/entities.py:179` | `dict` → `dict[str, Any]` |
| `src/infrastructure/weather/openweather_client.py:63` | Added explicit `dict[str, str \| float]` annotation |
| `src/infrastructure/weather/openweather_client.py:100` | Added explicit `dict[str, str \| float \| int]` annotation |

---

## Remediation Strategy

Three parallel agents launched (2026-05-23 11:00 UTC+5):

1. **Routers agent** — 213 errors across 14 router files
2. **Infrastructure agent** — 115 errors across 6+ files  
3. **Domain agent** — 49 errors across 5+ files

---

## Next Steps

1. Wait for agents to complete
2. Re-run mypy --strict
3. Categorize remaining errors
4. Fix critical (union-attr, attr-defined, index) — these are real bugs
5. Update pyproject.toml to remove `ignore_errors = true` overrides progressively
6. Add to CI pipeline as a quality gate
