/**
 * Unit tests for src/lib/tenant/tenant.ts — pure helpers only.
 *
 * `getActiveTenantId()` is deliberately excluded here because it depends on
 * `next/headers` request-scoped cookies/headers that only exist inside the
 * Next.js runtime.  The constants and pure functions are fully testable.
 */
import { beforeAll, describe, expect, it } from 'vitest';

import {
  TENANT_COOKIE,
  TENANT_HEADER,
  isValidUuid,
  listKnownTenants,
} from './tenant';

// Provide the env var that listKnownTenants() reads at call time.
const FAKE_TENANT_ID = '00000000-0000-0000-0000-000000000001';

beforeAll(() => {
  // env.d.ts marks this readonly for Next.js; cast to bypass in test environment.
  (process.env as Record<string, string>)['NEXT_PUBLIC_DEFAULT_TENANT_ID'] = FAKE_TENANT_ID;
});

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

describe('TENANT_COOKIE', () => {
  it('is the expected cookie name', () => {
    expect(TENANT_COOKIE).toBe('silklens.tenant');
  });
});

describe('TENANT_HEADER', () => {
  it('is the expected header name', () => {
    expect(TENANT_HEADER).toBe('x-tenant-id');
  });
});

// ---------------------------------------------------------------------------
// isValidUuid()
// ---------------------------------------------------------------------------

describe('isValidUuid()', () => {
  describe('valid UUIDs', () => {
    const valid = [
      // UUIDv4
      '550e8400-e29b-41d4-a716-446655440000',
      // UUIDv1
      '6ba7b810-9dad-11d1-80b4-00c04fd430c8',
      // UUIDv7 (time-ordered — used throughout SilkLens)
      '01906a3c-4f6b-7a00-b58f-d2a5b7c3e1f0',
      // Uppercase variant — regex uses /i flag
      '550E8400-E29B-41D4-A716-446655440000',
      // Mixed case
      '550e8400-E29B-41d4-A716-446655440000',
      // Variant bits 8-b (RFC 4122 compliant)
      '00000000-0000-1000-8000-000000000000',
      '00000000-0000-1000-9000-000000000000',
      '00000000-0000-1000-a000-000000000000',
      '00000000-0000-1000-b000-000000000000',
    ];

    for (const uuid of valid) {
      it(`accepts "${uuid}"`, () => {
        expect(isValidUuid(uuid)).toBe(true);
      });
    }
  });

  describe('invalid values', () => {
    const invalid = [
      '',
      'not-a-uuid',
      '00000000-0000-0000-0000-000000000000', // version nibble 0 — not in 1-7 range
      FAKE_TENANT_ID,                          // version nibble 0 — test fixture, not a real UUID
      '550e8400-e29b-41d4-z716-446655440000', // z is invalid hex
      '550e8400-e29b-41d4-a716-44665544000',  // too short (one char missing)
      '550e8400-e29b-41d4-a716-4466554400001', // too long (extra char)
      '550e8400e29b41d4a716446655440000',      // no dashes
      '00000000-0000-8000-8000-000000000000', // version 8 — outside 1-7
      'xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx', // non-hex chars
      null as unknown as string,
    ];

    for (const value of invalid) {
      it(`rejects "${String(value)}"`, () => {
        expect(isValidUuid(value as string)).toBe(false);
      });
    }
  });
});

// ---------------------------------------------------------------------------
// listKnownTenants()
// ---------------------------------------------------------------------------

describe('listKnownTenants()', () => {
  it('returns a non-empty array', () => {
    const tenants = listKnownTenants();
    expect(Array.isArray(tenants)).toBe(true);
    expect(tenants.length).toBeGreaterThan(0);
  });

  it('first entry has an id field', () => {
    const [first] = listKnownTenants();
    expect(first).toBeDefined();
    expect(typeof first!.id).toBe('string');
  });

  it('first entry has a non-empty slug', () => {
    const [first] = listKnownTenants();
    expect(first!.slug.length).toBeGreaterThan(0);
  });

  it('first entry has a non-empty displayName', () => {
    const [first] = listKnownTenants();
    expect(first!.displayName.length).toBeGreaterThan(0);
  });

  it('reads the default tenant id from the environment', () => {
    const [first] = listKnownTenants();
    expect(first!.id).toBe(FAKE_TENANT_ID);
  });

  it('root tenant has slug "silklens"', () => {
    const root = listKnownTenants().find((t) => t.slug === 'silklens');
    expect(root).toBeDefined();
  });
});
