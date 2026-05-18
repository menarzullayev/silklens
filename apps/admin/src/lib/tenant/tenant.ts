import { cookies, headers } from 'next/headers';

/**
 * Tenant resolution helpers.
 *
 * Order of precedence (server-side):
 *   1. `X-Tenant-Id` header (set by middleware after host / cookie resolution)
 *   2. `silklens.tenant` cookie (sticky selection from the tenant switcher)
 *   3. `NEXT_PUBLIC_DEFAULT_TENANT_ID` env default (matches backend seed)
 *
 * TODO(monetization): once tenants endpoint is live, validate that the chosen
 * id is actually accessible to the current user via a server-side fetch.
 */

export const TENANT_COOKIE = 'silklens.tenant';
export const TENANT_HEADER = 'x-tenant-id';

export function getActiveTenantId(): string {
  const fromHeader = headers().get(TENANT_HEADER);
  if (fromHeader && isValidUuid(fromHeader)) return fromHeader;

  const fromCookie = cookies().get(TENANT_COOKIE)?.value;
  if (fromCookie && isValidUuid(fromCookie)) return fromCookie;

  return process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID;
}

/** Placeholder tenant directory — replaced by an API call once Tenants ships. */
export interface TenantDescriptor {
  readonly id: string;
  readonly slug: string;
  readonly displayName: string;
}

export function listKnownTenants(): readonly TenantDescriptor[] {
  return [
    {
      id: process.env.NEXT_PUBLIC_DEFAULT_TENANT_ID,
      slug: 'silklens',
      displayName: 'SilkLens (root)',
    },
  ];
}

export function isValidUuid(value: string): boolean {
  return /^[0-9a-f]{8}-[0-9a-f]{4}-[1-7][0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}$/i.test(
    value,
  );
}
