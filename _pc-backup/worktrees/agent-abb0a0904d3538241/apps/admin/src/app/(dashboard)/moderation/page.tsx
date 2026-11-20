import { getTranslations } from 'next-intl/server';
import { ShieldCheck } from 'lucide-react';

import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';
import { EmptyState } from '@/components/ui/empty-state';

export default async function ModerationPage(): Promise<JSX.Element> {
  const t = await getTranslations('moderation');
  return (
    <PermissionGuard
      permission={PERMISSIONS.MODERATION_READ}
      fallback={<AccessDenied />}
    >
      <PageHeader title={t('title')} subtitle={t('subtitle')} />
      <EmptyState
        title={t('placeholderTitle')}
        description={t('placeholderHint')}
        icon={ShieldCheck}
      />
    </PermissionGuard>
  );
}
