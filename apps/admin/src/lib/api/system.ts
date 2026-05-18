import { apiFetch } from './client';
import type {
  FeatureFlagOut,
  FeatureFlagPutInput,
  SystemSettingOut,
  SystemSettingPutInput,
} from '@/types/api';

export function listSystemSettings(
  opts: { tenantId?: string } = {},
): Promise<readonly SystemSettingOut[]> {
  return apiFetch<readonly SystemSettingOut[]>({
    path: '/v1/admin/system-settings',
    query: { tenant_id: opts.tenantId },
  });
}

export function putSystemSetting(
  input: SystemSettingPutInput,
  opts: { tenantId?: string } = {},
): Promise<SystemSettingOut> {
  return apiFetch<SystemSettingOut>({
    path: '/v1/admin/system-settings',
    method: 'PUT',
    body: input,
    query: { tenant_id: opts.tenantId },
  });
}

export function listFeatureFlags(
  opts: { tenantId?: string } = {},
): Promise<readonly FeatureFlagOut[]> {
  return apiFetch<readonly FeatureFlagOut[]>({
    path: '/v1/admin/feature-flags',
    query: { tenant_id: opts.tenantId },
  });
}

export function putFeatureFlag(
  key: string,
  input: FeatureFlagPutInput,
  opts: { tenantId?: string } = {},
): Promise<FeatureFlagOut> {
  return apiFetch<FeatureFlagOut>({
    path: `/v1/admin/feature-flags/${encodeURIComponent(key)}`,
    method: 'PUT',
    body: input,
    query: { tenant_id: opts.tenantId },
  });
}
