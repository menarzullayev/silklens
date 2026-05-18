import { getTranslations } from 'next-intl/server';

import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';
import { vocabApi } from '@/lib/api';
import { HeritageForm } from '../heritage-form';

export default async function NewHeritagePage(): Promise<JSX.Element> {
  const t = await getTranslations('heritage');
  const [kinds, regions] = await Promise.all([
    vocabApi.getVocab('heritage_kinds').catch(() => null),
    vocabApi.getVocab('residency_regions').catch(() => null),
  ]);
  return (
    <PermissionGuard
      permission={PERMISSIONS.HERITAGE_WRITE}
      fallback={<AccessDenied />}
    >
      <PageHeader title={t('createTitle')} subtitle={t('createSubtitle')} />
      <HeritageForm
        mode="create"
        kindOptions={
          kinds?.items.map((i) => ({
            value: i.slug,
            label: i.display_name.en ?? i.display_name.uz ?? i.slug,
          })) ?? []
        }
        countryOptions={
          regions?.items.map((i) => ({
            value: i.slug.toUpperCase(),
            label: i.display_name.en ?? i.display_name.uz ?? i.slug,
          })) ?? []
        }
      />
    </PermissionGuard>
  );
}
