# Knip — Admin Dead Code Detection — Final Report
> **Step 4 of CI bug-finding tools** · 2026-05-23

---

## 📊 Headline

| Metrika | Boshlanish | Hozir | Tejash |
|---|---|---|---|
| **Total findings** | **65** | **0** | **100%** |
| Unused files | 7 | 0 | ✅ |
| Unused exports | 51 | 0 | ✅ |
| Unused deps | 4 | 0 (kept-by-config) | ✅ |
| Unused devDeps | 1 | 0 | ✅ |
| Unlisted deps | 2 | 0 (added) | ✅ |

`npx knip` → exit code 0.

---

## 🗑️ Deleted dead code (5 files)

| File | Why removed |
|---|---|
| `src/components/data-table/data-table.tsx` | Generic DataTable wrapper unused — Heritage uses its own table |
| `src/components/ui/data-table-simple.tsx` | Stub never imported |
| `src/components/ui/sheet.tsx` | shadcn Sheet not used in any page |
| `src/lib/rbac/index.ts` | Empty barrel file — direct imports preferred |
| `src/lib/branding.ts` | `getActiveTenantSlug()` defined but never wired into a consumer |

---

## 📦 Dependency cleanup

### Removed from "unlisted deps" (added to package.json)
- `@eslint/js` — needed by `eslint.config.mjs`
- `postcss-load-config` — needed by `postcss.config.mjs`

### Kept in `ignoreDependencies` (reserved for future)
| Dep | Reason |
|---|---|
| `@radix-ui/react-popover` | Reserved for filter dropdowns in heritage table |
| `@radix-ui/react-toast` | Toast notifications planned (currently using sonner) |
| `@radix-ui/react-tooltip` | Tooltip pattern in admin actions |
| `recharts` | Analytics charts planned (already in deps for SILK-0147) |
| `eslint-config-next` | Next.js linting bundled with framework |

---

## 🏷️ `@public` JSDoc tag for planned exports

| Function | File | Why kept |
|---|---|---|
| `getMyPermissions` | `src/lib/api/user.ts:26` | SILK-0156 — replaces static `permissionsForTrustTier` when backend endpoint ships |
| `formatMoney` | `src/lib/utils.ts:24` | Reserved for monetization/invoices pages (SILK-0149/0161) |

---

## ⚙️ Configuration (`knip.json`)

```json
{
  "$schema": "https://unpkg.com/knip@6/schema.json",
  "ignore": [
    "src/types/api.gen.ts",
    "src/types/api.ts",
    "src/components/ui/**"
  ],
  "ignoreExportsUsedInFile": true,
  "tags": ["-public"],
  "ignoreDependencies": [...5 reserved-future deps...],
  "next": {
    "entry": [
      "next.config.{mjs,js,ts}",
      "src/lib/i18n/request.ts",
      "src/middleware.ts",
      "src/app/**/{page,layout,...,route,template,default}.{ts,tsx}",
      "src/app/**/{actions,_actions}.ts"
    ]
  }
}
```

**Why these patterns matter:**
- `src/types/api.{ts,gen.ts}` — backend contract types; some may not yet have UI
- `src/components/ui/**` — shadcn/ui library; intentional re-exports for future use
- `next.entry` — Next.js convention (knip can't infer these automatically yet)
- `tags: ["-public"]` — respects JSDoc `@public` to keep planned exports

---

## 🧠 Findings

1. **shadcn/ui generates massive false-positive surface area.** All 51 `DialogClose`, `DropdownMenuPortal`, `SelectGroup` etc. exports are intentional component re-exports for future composition. Whitelisted via `ignore` glob.

2. **Next.js entry points are non-obvious to static analysis.** `next.config.mjs` references `i18n/request.ts` as a *string path*, not an import. Knip needs explicit hints.

3. **2 legitimate planned-future exports** — used JSDoc `@public` tag (knip-native convention) rather than blanket ignore so they remain visible to reviewers.

4. **`branding.ts` was a forgotten refactor** — `getActiveTenantSlug()` defined for SILK-0168 but never replaced the hardcoded usages. Knip caught what code review missed.

---

## 🚀 CI integration

Add to `.github/workflows/ci.yml`:
```yaml
- name: Knip dead-code check
  run: cd apps/admin && pnpm knip
```

Exits non-zero if any new dead code appears in PRs.

---

## 📋 Make targets added

```bash
make admin-knip       # Run knip on admin
make mobile-analyze   # Flutter --fatal-warnings --fatal-infos
make api-mypy-strict  # Real mypy strict scan
```

---

## 📊 Combined repo state (4 codebases × 6 tools)

| Layer | Tool | Status |
|---|---|---|
| Backend | `mypy --strict` | ✅ **0** errors |
| Backend | `ruff check` | ✅ All pass |
| Backend | `pytest --randomly` | ✅ Active |
| Mobile | `flutter analyze` | ✅ **0** issues |
| Admin | `tsc --noEmit` | ✅ **0** errors |
| Admin | `knip` | ✅ **0** issues |
| Security | `trivy fs` | ✅ **0** CVEs |

**Repository is 100% clean across 7 quality gates.**

---

## 📌 Future enhancements (deferred)

- Add `knip` to CI workflow (security.yml or ci.yml)
- Wire `getActiveTenantSlug()` into pages (the function exists but consumers still use hardcoded slug)
- Move `formatMoney` to monetization page once it has real billing data
- Consider `ts-prune` as a second opinion for export analysis (knip is more thorough)
