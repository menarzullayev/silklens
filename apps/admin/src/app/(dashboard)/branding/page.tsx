import { getTranslations } from 'next-intl/server';

import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';
import { tenantsApi } from '@/lib/api';
import { ApiError } from '@/lib/api/errors';
import { ErrorState } from '@/components/ui/empty-state';
import { BrandingForm } from './branding-form';
import type { BrandingOut } from '@/types/api';

const DEFAULT_SLUG = 'silklens';

export default async function BrandingPage(): Promise<JSX.Element> {
  const t = await getTranslations('branding');

  // The branding endpoint is per-tenant slug; for now we work against the
  // root tenant. A future iteration will read `silklens.tenant` cookie →
  // resolve slug via `GET /v1/admin/tenants`.
  const branding: BrandingOut | ApiError | Error = await tenantsApi
    .getBranding(DEFAULT_SLUG)
    .catch((cause: unknown) => (cause instanceof Error ? cause : new Error(String(cause))));

  return (
    <PermissionGuard
      permission={PERMISSIONS.BRANDING_MANAGE}
      fallback={<AccessDenied />}
    >
      <PageHeader title={t('title')} subtitle={t('subtitle')} />
      {branding instanceof Error ? (
        <ErrorState title={t('errorTitle')} message={branding.message} />
      ) : (
        <BrandingForm
          slug={DEFAULT_SLUG}
          initial={branding}
          labels={{
            appName: t('appName'),
            logoUrl: t('logoUrl'),
            primaryColor: t('primaryColor'),
            splashImage: t('splashImage'),
            saved: t('saved'),
          }}
        />
      )}
    </PermissionGuard>
  );
}
