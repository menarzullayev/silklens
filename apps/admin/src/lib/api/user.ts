/**
 * SILK-0156: User API helpers.
 *
 * `getMyPermissions` fetches the authenticated user's trust_tier from
 * GET /v1/auth/me and maps it to a permission set via the static catalog in
 * `src/lib/rbac/permissions.ts`.
 *
 * NOTE: A dedicated GET /v1/auth/me/permissions endpoint does not exist yet.
 * When it ships, replace the `permissionsForTrustTier()` call below with a
 * direct fetch of the permissions array from the backend so RBAC is fully
 * server-driven without a client-side mapping table.
 */

import { permissionsForTrustTier } from '@/lib/rbac/permissions';

/**
 * Fetch the authenticated user's permissions from the backend.
 *
 * Strategy: call GET /v1/auth/me with the provided access token, read the
 * `trust_tier` field, then derive the permission set using the static mapping
 * in `permissionsForTrustTier()`.  Falls back to an empty array on any
 * network or parse failure — callers should treat an empty array as "no
 * permissions granted" and redirect to /login if the session is expected to be
 * valid.
 *
 * NOTE: Currently unused — kept for SILK-0156 (replace static
 * permissionsForTrustTier with this once backend endpoint ships).
 *
 * @public
 */
export async function getMyPermissions(accessToken: string): Promise<string[]> {
  try {
    const base =
      typeof window === 'undefined'
        ? (process.env.API_INTERNAL_URL ?? process.env.NEXT_PUBLIC_API_URL ?? '')
        : (process.env.NEXT_PUBLIC_API_URL ?? '');

    const r = await fetch(`${base.replace(/\/+$/, '')}/v1/auth/me`, {
      headers: {
        Authorization: `Bearer ${accessToken}`,
        Accept: 'application/json',
      },
      cache: 'no-store',
    });

    if (!r.ok) return [];

    const data = (await r.json()) as { user?: { trust_tier?: string }; trust_tier?: string };
    // /v1/auth/me returns { user: { trust_tier, … }, session_id, trust_tier }
    const tier = data.user?.trust_tier ?? data.trust_tier;
    if (!tier) return [];

    // Static mapping from trust_tier → permission slugs.
    // Replace with direct server fetch when backend exposes
    // GET /v1/auth/me/permissions.
    return [...permissionsForTrustTier(tier)];
  } catch {
    return [];
  }
}
