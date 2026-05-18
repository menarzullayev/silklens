import { getTranslations } from 'next-intl/server';

import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';
import { systemApi } from '@/lib/api';
import { ApiError } from '@/lib/api/errors';
import { ErrorState } from '@/components/ui/empty-state';
import { SettingsTree } from './settings-tree';

export default async function SettingsPage(): Promise<JSX.Element> {
  const t = await getTranslations('settings');
  const settings = await systemApi
    .listSystemSettings()
    .catch((cause: unknown) => cause);

  return (
    <PermissionGuard
      permission={PERMISSIONS.SETTINGS_MANAGE}
      fallback={<AccessDenied />}
    >
      <PageHeader title={t('title')} subtitle={t('subtitle')} />
      {settings instanceof ApiError ? (
        <ErrorState title={t('errorTitle')} message={settings.message} />
      ) : settings instanceof Error ? (
        <ErrorState title={t('errorTitle')} message={settings.message} />
      ) : (
        <SettingsTree settings={settings} />
      )}
    </PermissionGuard>
  );
}
