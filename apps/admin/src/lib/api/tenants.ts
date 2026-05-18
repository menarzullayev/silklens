import { apiFetch } from './client';
import type {
  BrandingOut,
  BrandingPutInput,
  TenantCreateInput,
  TenantOut,
  TenantPatchInput,
  TenantsPage,
} from '@/types/api';

export function listTenants(
  opts: { limit?: number; offset?: number } = {},
): Promise<TenantsPage> {
  return apiFetch<TenantsPage>({
    path: '/v1/admin/tenants',
    query: { limit: opts.limit ?? 20, offset: opts.offset ?? 0 },
  });
}

export function createTenant(input: TenantCreateInput): Promise<TenantOut> {
  return apiFetch<TenantOut>({
    path: '/v1/admin/tenants',
    method: 'POST',
    body: input,
  });
}

export function patchTenant(
  slug: string,
  input: TenantPatchInput,
): Promise<TenantOut> {
  return apiFetch<TenantOut>({
    path: `/v1/admin/tenants/${encodeURIComponent(slug)}`,
    method: 'PATCH',
    body: input,
  });
}

export function getBranding(slug: string): Promise<BrandingOut> {
  return apiFetch<BrandingOut>({
    path: `/v1/admin/tenants/${encodeURIComponent(slug)}/branding`,
  });
}

export function putBranding(
  slug: string,
  input: BrandingPutInput,
): Promise<BrandingOut> {
  return apiFetch<BrandingOut>({
    path: `/v1/admin/tenants/${encodeURIComponent(slug)}/branding`,
    method: 'PUT',
    body: input,
  });
}
