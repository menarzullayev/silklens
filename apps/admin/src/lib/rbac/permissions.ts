/**
 * Permission catalog mirrored from the server-side `permissions` table
 * (architecture §02 — Identity, RBAC, GDPR).
 *
 * Convention: `<domain>:<action>[:<scope>]` — keep these strings *identical*
 * to the `permissions.slug` values seeded by the backend so RBAC drift is
 * trivial to grep.
 *
 * SILK-0156: `permissionsForTrustTier()` is the authoritative static mapping
 * from a backend `trust_tier` string to a permission set.  It is used both
 * during JWT construction in `src/lib/auth/auth.ts` and when fetching live
 * permissions via `src/lib/api/user.ts`.
 *
 * When GET /v1/auth/me/permissions is available on the backend, callers of
 * `getMyPermissions()` in `src/lib/api/user.ts` will fetch directly from the
 * API and this mapping becomes a fallback only.
 */
export const PERMISSIONS = {
  // Heritage / content
  HERITAGE_READ: 'heritage:read',
  HERITAGE_WRITE: 'heritage:create',
  HERITAGE_UPDATE: 'heritage:update',
  HERITAGE_DELETE: 'heritage:delete',
  HERITAGE_MODERATE: 'heritage:moderate',

  // Users
  USERS_READ: 'users:read',
  USERS_WRITE: 'users:write',
  USERS_BAN: 'users:ban',

  // Moderation
  MODERATION_READ: 'moderation:read',
  MODERATION_ACT: 'moderation:act',

  // AI models
  AI_MODELS_READ: 'ai-models:read',
  AI_MODELS_WRITE: 'ai-models:write',

  // Monetization
  MONETIZATION_READ: 'monetization:read',
  MONETIZATION_WRITE: 'monetization:write',

  // Tenants — super-admin scope only.
  TENANTS_MANAGE: 'tenants:manage',

  // Per-tenant branding (Project-Decisions §21, §50 — white-label).
  BRANDING_MANAGE: 'branding:manage',

  // Analytics
  ANALYTICS_READ: 'analytics:read',

  // System settings
  SETTINGS_MANAGE: 'settings:manage',
} as const;

export type Permission = (typeof PERMISSIONS)[keyof typeof PERMISSIONS];

/**
 * Map a backend `trust_tier` value to the corresponding permission set.
 *
 * Exported so both `src/lib/auth/auth.ts` (JWT construction) and
 * `src/lib/api/user.ts` (live permission fetch) use the same mapping.
 *
 * SILK-0156: When GET /v1/auth/me/permissions lands on the backend, this
 * function becomes a fallback and `getMyPermissions()` will prefer the API
 * response directly.
 */
export function permissionsForTrustTier(tier: string): readonly string[] {
  // Base set: any authenticated user can read the catalogue.
  const BASE: readonly string[] = ['heritage:read', 'reviews:read', 'analytics:read'];

  // Contributors can create and moderate content.
  const CONTENT: readonly string[] = [
    ...BASE,
    'heritage:create',
    'heritage:update',
    'reviews:moderate',
  ];

  // Staff / admin get the full set including tenant, system and billing scopes.
  const ADMIN: readonly string[] = [
    ...CONTENT,
    'heritage:delete',
    'heritage:moderate',
    'heritage:write',
    'users:read',
    'users:write',
    'users:ban',
    'moderation:read',
    'moderation:act',
    'ai-models:read',
    'ai-models:write',
    'ai:configure',
    'gdpr:approve',
    'monetization:read',
    'monetization:write',
    'tenants:manage',
    'tenant:read',
    'tenant:manage',
    'tenant:create',
    'tenant:branding',
    'branding:manage',
    'reseller:read',
    'reseller:approve',
    'reseller:configure_revenue_share',
    'settings:manage',
    'system:settings',
    'system:feature_flags',
  ];

  switch (tier) {
    case 'super_admin':
    case 'system_actor':
    case 'staff':
    case 'admin':
      return ADMIN;
    case 'contributor':
      return CONTENT;
    default:
      return BASE;
  }
}

/** Pure resolver: does `granted` satisfy `required`? */
export function hasPermission(
  granted: readonly string[] | undefined,
  required: Permission | readonly Permission[],
): boolean {
  if (!granted || granted.length === 0) return false;
  const set = new Set(granted);
  if (Array.isArray(required)) {
    return required.every((p) => set.has(p));
  }
  return set.has(required as Permission);
}

/** Satisfies any of the listed permissions (OR semantics). */
export function hasAnyPermission(
  granted: readonly string[] | undefined,
  required: readonly Permission[],
): boolean {
  if (!granted || granted.length === 0) return false;
  const set = new Set(granted);
  return required.some((p) => set.has(p));
}
