import { getTranslations } from 'next-intl/server';

import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';
import { systemApi } from '@/lib/api';
import { ApiError } from '@/lib/api/errors';
import { ErrorState } from '@/components/ui/empty-state';
import { FeatureFlagsView } from './feature-flags-view';

export default async function FeatureFlagsPage(): Promise<JSX.Element> {
  const t = await getTranslations('featureFlags');
  const flags = await systemApi
    .listFeatureFlags()
    .catch((cause: unknown) => cause);
  return (
    <PermissionGuard
      permission={PERMISSIONS.SETTINGS_MANAGE}
      fallback={<AccessDenied />}
    >
      <PageHeader title={t('title')} subtitle={t('subtitle')} />
      {flags instanceof ApiError ? (
        <ErrorState title={t('errorTitle')} message={flags.message} />
      ) : flags instanceof Error ? (
        <ErrorState title={t('errorTitle')} message={flags.message} />
      ) : (
        <FeatureFlagsView flags={flags} />
      )}
    </PermissionGuard>
  );
}
