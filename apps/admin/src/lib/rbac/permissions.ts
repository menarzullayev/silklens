/**
 * Permission catalog mirrored from the server-side `permissions` table
 * (architecture §02 — Identity, RBAC, GDPR).
 *
 * Convention: `<domain>:<action>[:<scope>]` — keep these strings *identical*
 * to the `permissions.slug` values seeded by the backend so RBAC drift is
 * trivial to grep.
 */
export const PERMISSIONS = {
  // Heritage / content
  HERITAGE_READ: 'heritage:read',
  HERITAGE_WRITE: 'heritage:write',
  HERITAGE_DELETE: 'heritage:delete',

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
