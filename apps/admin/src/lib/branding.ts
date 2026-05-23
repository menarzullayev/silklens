/**
 * SILK-0168: Tenant slug resolver used by branding-aware code paths.
 *
 * Resolution order (server-side):
 *   1. `tenant_slug` cookie (sticky selection from a tenant switcher / signed
 *      session cookie set by `auth.ts` after login).
 *   2. `NEXT_PUBLIC_DEFAULT_TENANT_SLUG` env (defaults to `silklens`).
 *
 * Previously the slug was hardcoded inline as `'silklens'` in several call
 * sites. This helper centralises the lookup so that white-labelled deployments
 * — Project-Decisions §21, §50 — pick up their own slug without code edits.
 *
 * Notes on `cookies()`: `next/headers` only works inside a server component
 * or Route Handler. We swallow the error in non-server contexts so callers
 * can use this helper from edge / middleware-adjacent code without crashing.
 */

import { cookies } from 'next/headers';

export const TENANT_SLUG_COOKIE = 'tenant_slug';

export async function getActiveTenantSlug(): Promise<string> {
  try {
    const store = await cookies();
    const slug = store.get(TENANT_SLUG_COOKIE)?.value;
    if (slug && slug.trim().length > 0) {
      return slug.trim();
    }
  } catch {
    // Not in a server-component / route-handler context — fall through.
  }
  return process.env.NEXT_PUBLIC_DEFAULT_TENANT_SLUG ?? 'silklens';
}

/**
 * Synchronous variant for non-async sites (e.g. `auth.ts` JWT callback) where
 * the env default is the only resolution path. Cookie reads must use the
 * async {@link getActiveTenantSlug}.
 */
export function getDefaultTenantSlug(): string {
  return process.env.NEXT_PUBLIC_DEFAULT_TENANT_SLUG ?? 'silklens';
}
