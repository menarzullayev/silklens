import { getTranslations } from 'next-intl/server';

import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';
import { tenantsApi } from '@/lib/api';
import { ApiError } from '@/lib/api/errors';
import { ErrorState } from '@/components/ui/empty-state';
import { TenantsView } from './tenants-view';

export default async function TenantsPage(): Promise<JSX.Element> {
  const t = await getTranslations('tenants');
  const page = await tenantsApi
    .listTenants({ limit: 50 })
    .catch((cause: unknown) => cause as Error);

  return (
    <PermissionGuard
      permission={PERMISSIONS.TENANTS_MANAGE}
      fallback={<AccessDenied />}
    >
      <PageHeader title={t('title')} subtitle={t('subtitle')} />
      {page instanceof ApiError ? (
        <ErrorState title={t('errorTitle')} message={page.message} />
      ) : page instanceof Error ? (
        <ErrorState title={t('errorTitle')} message={page.message} />
      ) : (
        <TenantsView items={page.items} />
      )}
    </PermissionGuard>
  );
}
