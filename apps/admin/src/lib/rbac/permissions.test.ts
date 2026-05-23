/**
 * Unit tests for src/lib/rbac/permissions.ts
 *
 * Covers: PERMISSIONS catalog shape, permissionsForTrustTier() tier mapping,
 * hasPermission() single + array semantics, hasAnyPermission() OR semantics.
 */
import { describe, expect, it } from 'vitest';

import {
  PERMISSIONS,
  hasAnyPermission,
  hasPermission,
  permissionsForTrustTier,
} from './permissions';

// ---------------------------------------------------------------------------
// PERMISSIONS catalog
// ---------------------------------------------------------------------------

describe('PERMISSIONS', () => {
  it('contains the heritage read permission', () => {
    expect(PERMISSIONS.HERITAGE_READ).toBe('heritage:read');
  });

  it('contains the heritage write permission', () => {
    expect(PERMISSIONS.HERITAGE_WRITE).toBe('heritage:create');
  });

  it('contains the tenants manage permission', () => {
    expect(PERMISSIONS.TENANTS_MANAGE).toBe('tenants:manage');
  });

  it('contains the settings manage permission', () => {
    expect(PERMISSIONS.SETTINGS_MANAGE).toBe('settings:manage');
  });

  it('all permission values are non-empty strings', () => {
    for (const value of Object.values(PERMISSIONS)) {
      expect(typeof value).toBe('string');
      expect((value as string).length).toBeGreaterThan(0);
    }
  });

  it('all permission values follow the domain:action[:scope] format', () => {
    for (const value of Object.values(PERMISSIONS)) {
      expect(value).toMatch(/^[a-z-]+:[a-z_-]+$/);
    }
  });

  it('has no duplicate permission values', () => {
    const values = Object.values(PERMISSIONS);
    expect(new Set(values).size).toBe(values.length);
  });
});

// ---------------------------------------------------------------------------
// permissionsForTrustTier()
// ---------------------------------------------------------------------------

describe('permissionsForTrustTier()', () => {
  // The BASE set every authenticated user gets.
  const BASE_PERMS = ['heritage:read', 'reviews:read', 'analytics:read'];

  // Admin-only capabilities.
  const ADMIN_ONLY_PERMS = [
    'tenants:manage',
    'settings:manage',
    'moderation:act',
    'users:ban',
  ];

  // Contributor-only (not available to plain viewers).
  const CONTRIBUTOR_PERMS = ['heritage:create', 'heritage:update'];

  describe('super_admin tier', () => {
    const perms = permissionsForTrustTier('super_admin');

    it('is an array', () => {
      expect(Array.isArray(perms)).toBe(true);
    });

    it('includes all BASE permissions', () => {
      for (const p of BASE_PERMS) {
        expect(perms).toContain(p);
      }
    });

    it('includes all ADMIN-only permissions', () => {
      for (const p of ADMIN_ONLY_PERMS) {
        expect(perms).toContain(p);
      }
    });

    it('includes branding:manage', () => {
      expect(perms).toContain('branding:manage');
    });
  });

  describe('admin tier', () => {
    it('returns the same set as super_admin', () => {
      expect(permissionsForTrustTier('admin')).toEqual(permissionsForTrustTier('super_admin'));
    });
  });

  describe('staff tier', () => {
    it('returns the same set as super_admin', () => {
      expect(permissionsForTrustTier('staff')).toEqual(permissionsForTrustTier('super_admin'));
    });
  });

  describe('system_actor tier', () => {
    it('returns the same set as super_admin', () => {
      expect(permissionsForTrustTier('system_actor')).toEqual(
        permissionsForTrustTier('super_admin'),
      );
    });
  });

  describe('contributor tier', () => {
    const perms = permissionsForTrustTier('contributor');

    it('includes BASE permissions', () => {
      for (const p of BASE_PERMS) {
        expect(perms).toContain(p);
      }
    });

    it('includes contributor-level create/update permissions', () => {
      for (const p of CONTRIBUTOR_PERMS) {
        expect(perms).toContain(p);
      }
    });

    it('does NOT include ADMIN-only permissions', () => {
      for (const p of ADMIN_ONLY_PERMS) {
        expect(perms).not.toContain(p);
      }
    });

    it('does NOT include heritage:delete', () => {
      expect(perms).not.toContain('heritage:delete');
    });
  });

  describe('unknown / viewer tier (default)', () => {
    const cases = ['viewer', 'guest', '', 'random_string', 'ADMIN'];

    for (const tier of cases) {
      it(`tier "${tier}" returns only BASE permissions`, () => {
        const perms = permissionsForTrustTier(tier);
        expect(perms).toEqual(BASE_PERMS);
      });
    }

    it('does NOT include any admin permissions for unknown tier', () => {
      const perms = permissionsForTrustTier('unknown');
      for (const p of ADMIN_ONLY_PERMS) {
        expect(perms).not.toContain(p);
      }
    });
  });
});

// ---------------------------------------------------------------------------
// hasPermission()
// ---------------------------------------------------------------------------

describe('hasPermission()', () => {
  const adminPerms = permissionsForTrustTier('admin');
  const basePerms = permissionsForTrustTier('viewer');

  describe('single-permission (string) check', () => {
    it('returns true when the permission is granted', () => {
      expect(hasPermission(adminPerms, PERMISSIONS.HERITAGE_READ)).toBe(true);
    });

    it('returns false when the permission is not granted', () => {
      expect(hasPermission(basePerms, PERMISSIONS.TENANTS_MANAGE)).toBe(false);
    });

    it('returns false for undefined granted list', () => {
      expect(hasPermission(undefined, PERMISSIONS.HERITAGE_READ)).toBe(false);
    });

    it('returns false for empty granted list', () => {
      expect(hasPermission([], PERMISSIONS.HERITAGE_READ)).toBe(false);
    });
  });

  describe('array-permission (AND semantics) check', () => {
    it('returns true when ALL required permissions are granted', () => {
      expect(
        hasPermission(adminPerms, [PERMISSIONS.HERITAGE_READ, PERMISSIONS.HERITAGE_WRITE]),
      ).toBe(true);
    });

    it('returns false when ANY required permission is missing', () => {
      // basePerms has heritage:read but not tenants:manage
      expect(hasPermission(basePerms, [PERMISSIONS.HERITAGE_READ, PERMISSIONS.TENANTS_MANAGE])).toBe(
        false,
      );
    });

    it('returns false when all required permissions are missing', () => {
      expect(
        hasPermission(basePerms, [PERMISSIONS.TENANTS_MANAGE, PERMISSIONS.SETTINGS_MANAGE]),
      ).toBe(false);
    });

    it('returns false for empty granted list', () => {
      expect(hasPermission([], [PERMISSIONS.HERITAGE_READ])).toBe(false);
    });

    it('returns false for undefined granted list', () => {
      expect(hasPermission(undefined, [PERMISSIONS.HERITAGE_READ])).toBe(false);
    });

    it('returns true for an empty required array (vacuous truth)', () => {
      // Array.every([]) === true — empty requirement is trivially satisfied.
      expect(hasPermission([], [])).toBe(false); // empty granted still blocks
      expect(hasPermission(basePerms, [])).toBe(true); // non-empty granted + empty req = true
    });
  });
});

// ---------------------------------------------------------------------------
// hasAnyPermission() — OR semantics
// ---------------------------------------------------------------------------

describe('hasAnyPermission()', () => {
  const adminPerms = permissionsForTrustTier('admin');
  const basePerms = permissionsForTrustTier('viewer');

  it('returns true when at least one permission matches', () => {
    expect(
      hasAnyPermission(basePerms, [PERMISSIONS.HERITAGE_READ, PERMISSIONS.TENANTS_MANAGE]),
    ).toBe(true);
  });

  it('returns false when NO permission in the required list is granted', () => {
    expect(
      hasAnyPermission(basePerms, [PERMISSIONS.TENANTS_MANAGE, PERMISSIONS.SETTINGS_MANAGE]),
    ).toBe(false);
  });

  it('returns true for admin perms against any single perm in the set', () => {
    const required: (typeof PERMISSIONS)[keyof typeof PERMISSIONS][] = [
      PERMISSIONS.HERITAGE_READ,
      PERMISSIONS.USERS_BAN,
    ];
    expect(hasAnyPermission(adminPerms, required)).toBe(true);
  });

  it('returns false for undefined granted list', () => {
    expect(hasAnyPermission(undefined, [PERMISSIONS.HERITAGE_READ])).toBe(false);
  });

  it('returns false for empty granted list', () => {
    expect(hasAnyPermission([], [PERMISSIONS.HERITAGE_READ])).toBe(false);
  });

  it('returns false for empty required list (Array.some([]) === false)', () => {
    expect(hasAnyPermission(adminPerms, [])).toBe(false);
  });
});
