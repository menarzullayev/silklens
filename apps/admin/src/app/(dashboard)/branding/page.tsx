import { getTranslations } from 'next-intl/server';

import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';
import { auth } from '@/lib/auth/auth';
import { tenantsApi } from '@/lib/api';
import type { ApiError } from '@/lib/api/errors';
import { ErrorState } from '@/components/ui/empty-state';
import { BrandingForm } from './branding-form';
import type { BrandingOut } from '@/types/api';

// SILK-0168: slug is now resolved from the session JWT (tenantSlug field).
// Falls back to NEXT_PUBLIC_DEFAULT_TENANT_SLUG → 'silklens' when no session
// is available (e.g. pre-render without auth context in tests).

export default async function BrandingPage(): Promise<JSX.Element> {
  const t = await getTranslations('branding');
  const session = await auth();
  const slug: string =
    session?.user?.tenantSlug ??
    process.env.NEXT_PUBLIC_DEFAULT_TENANT_SLUG ??
    'silklens';

  const branding: BrandingOut | ApiError | Error = await tenantsApi
    .getBranding(slug)
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
          slug={slug}
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
