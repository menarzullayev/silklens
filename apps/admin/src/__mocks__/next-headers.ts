/**
 * Lightweight stub for `next/headers` used by Vitest.
 *
 * Next.js's `cookies()` and `headers()` are request-scoped async functions
 * that only exist inside the Next.js runtime. When pure-logic helpers (e.g.
 * `lib/tenant/tenant.ts`) import them at module level, Vitest would fail to
 * resolve the real package. This stub provides no-op implementations so those
 * modules can be imported; individual tests that exercise `getActiveTenantId`
 * should override with `vi.mock()` or call the pure helpers directly.
 */
export const cookies = async () => ({
  get: (_name: string) => undefined,
});

export const headers = async () => ({
  get: (_name: string) => null,
});
