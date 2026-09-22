# SilkLens Admin Panel

Control plane for the SilkLens cultural-heritage platform. Built with
**Next.js 14 (App Router) + TypeScript + Tailwind CSS + shadcn/ui** and
backed by the SilkLens FastAPI service.

This package is the white-label-capable admin that the rest of the SilkLens
platform points at: branding, monetization, AI-model selection, moderation,
heritage CRUD, and tenant management all live here.

---

## Quick start

```bash
# 1. Install dependencies (Node 20+, pnpm 9+).
pnpm install            # or `npm install` if you don't have pnpm

# 2. Copy the env template and fill in secrets.
cp .env.example .env.local
#   AUTH_SECRET=...                       # openssl rand -base64 32
#   NEXT_PUBLIC_API_URL=http://localhost:8000

# 3. Boot the dev server (port 3001 — leaves 3000 for the marketing site).
pnpm dev

# 4. Open http://localhost:3001/login
```

The admin runs entirely on top of `services/api`. Boot the API first via
`make dev` from the repo root, otherwise data fetches fail (the UI itself
renders — every API call goes through the typed wrapper in
`src/lib/api/client.ts` which raises typed errors that components render
gracefully).

### Pointing at a remote API

Set both:

```dotenv
NEXT_PUBLIC_API_URL="https://api.silklens.app"
API_INTERNAL_URL="https://api.silklens.app"
```

`NEXT_PUBLIC_API_URL` is what the browser sees; `API_INTERNAL_URL` is used
inside Server Components and is what you would point at the Docker-internal
hostname when running in a compose stack.

---

## Stack

| Layer | Choice |
|---|---|
| Framework | Next.js 14 (App Router) — Server Components first |
| Language | TypeScript 5.5 — `strict` + `noUncheckedIndexedAccess` |
| UI | shadcn/ui (new-york style) + Tailwind 3.4 + lucide-react |
| Forms | react-hook-form + zod (`@hookform/resolvers`) |
| Server state | TanStack Query 5 (client components only) |
| Tables | TanStack Table 8 — wired up in `src/components/data-table/` |
| Charts | Recharts 2 (analytics page) |
| Auth | NextAuth v5 (Auth.js) — JWT session strategy |
| i18n | next-intl — uz · en · ru · zh |
| Themes | next-themes — light · dark · system |
| Tests | Playwright 1.47 (smoke) |

---

## Project layout

```
src/
├── app/
│   ├── (auth)/login/      # Login page + Server Action sign-in
│   ├── (dashboard)/       # Authenticated routes (sidebar + topbar)
│   │   ├── dashboard/     # Overview metrics
│   │   ├── heritage/
│   │   ├── users/
│   │   ├── moderation/
│   │   ├── ai-models/
│   │   ├── monetization/
│   │   ├── tenants/       # Super-admin only
│   │   ├── branding/      # Per-tenant white-label form
│   │   ├── analytics/
│   │   └── settings/
│   └── api/auth/[...nextauth]/route.ts
├── components/
│   ├── ui/                # shadcn/ui primitives (Button, Card, Form, …)
│   ├── layout/            # Sidebar, topbar, breadcrumbs, switchers
│   ├── data-table/        # Generic table over @tanstack/react-table
│   └── rbac/              # <PermissionGuard /> + <AccessDenied />
├── lib/
│   ├── api/               # Typed fetch wrapper + ApiError hierarchy
│   ├── auth/              # NextAuth v5 config (single source of truth)
│   ├── i18n/              # next-intl config + request handler
│   ├── rbac/              # Permission catalog + pure resolvers
│   ├── tenant/            # Active-tenant resolution + UUID validation
│   └── utils.ts           # cn() + locale-aware formatters
├── messages/              # uz.json · en.json · ru.json · zh.json
├── middleware.ts          # Auth gate + tenant/locale resolution
└── types/                 # env.d.ts + placeholder OpenAPI types
```

---

## Available scripts

```bash
pnpm dev           # Next.js dev server on :3001
pnpm build         # Production build (output: standalone, Docker-friendly)
pnpm start         # Run the production build
pnpm lint          # ESLint flat config (strict @typescript-eslint)
pnpm format        # Prettier write
pnpm typecheck     # tsc --noEmit
pnpm test:e2e      # Playwright (requires `pnpm test:e2e:install` first)
```

---

## Adding a new shadcn/ui component

The repo ships with the components SilkLens already uses, vendored directly
(no `pnpx shadcn add` required during install). To add a new one:

```bash
pnpx shadcn@latest add hover-card
```

The CLI writes into `src/components/ui/` and respects `components.json`.
Commit the generated file as-is.

---

## Adding a new locale

1. Drop `src/messages/<code>.json` keyed exactly like `en.json`.
2. Append the locale to `LOCALES` in `src/lib/i18n/config.ts`.
3. Add its label in `LOCALE_LABELS`.
4. The locale switcher in the topbar picks it up automatically.

---

## RBAC

Permissions are declared in `src/lib/rbac/permissions.ts` and **must match the
`permissions.slug` rows seeded by the FastAPI Identity service**. Wrap any
permission-gated UI in `<PermissionGuard>` — it's a Server Component, so
permission strings never reach the client bundle.

```tsx
<PermissionGuard permission={PERMISSIONS.HERITAGE_WRITE} fallback={<AccessDenied />}>
  <CreateHeritageButton />
</PermissionGuard>
```

---

## Multi-tenancy

Every API call carries `X-Tenant-Id`. Resolution order:

1. `X-Tenant-Id` request header (set by middleware)
2. `silklens.tenant` cookie (sticky tenant switcher selection)
3. `NEXT_PUBLIC_DEFAULT_TENANT_ID` env (matches the backend's seeded root tenant)

See `src/lib/tenant/tenant.ts` and the topbar tenant switcher.

---

## Open follow-ups

- NextAuth providers (Google, Apple, Telegram) need real credentials. The
  buttons exist; `signInWithProviderAction` currently falls through to the
  Credentials provider until the secrets are wired.
- OpenAPI types (`src/types/api.ts`) are hand-written placeholders. Once the
  FastAPI routers ship, regenerate via:

  ```bash
  pnpm dlx openapi-typescript http://localhost:8000/openapi.json \
    -o src/types/api.ts
  ```
- Tenant directory in `lib/tenant/tenant.ts` returns a single placeholder
  tenant. Swap to an `apiFetch<TenantSummary[]>('/admin/tenants')` once the
  endpoint exists.
- The branding form persists nowhere; wire it to
  `POST /admin/tenants/{id}/branding` once the route is live.

---

## Production build

`next.config.mjs` sets `output: 'standalone'` so a Dockerfile only needs the
emitted `.next/standalone` and `public/` directories. The deploy pipeline is
defined in `infra/` at the repo root.
