import { getTranslations } from 'next-intl/server';

import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';
import { BrandingForm } from './branding-form';

export default async function BrandingPage(): Promise<JSX.Element> {
  const t = await getTranslations('branding');
  return (
    <PermissionGuard
      permission={PERMISSIONS.BRANDING_MANAGE}
      fallback={<AccessDenied />}
    >
      <PageHeader title={t('title')} subtitle={t('subtitle')} />
      <BrandingForm
        labels={{
          appName: t('appName'),
          logoUrl: t('logoUrl'),
          primaryColor: t('primaryColor'),
          splashImage: t('splashImage'),
          saved: t('saved'),
        }}
      />
    </PermissionGuard>
  );
}
