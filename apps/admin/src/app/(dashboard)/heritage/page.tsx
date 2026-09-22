import Link from 'next/link';
import { getTranslations } from 'next-intl/server';
import { Plus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';
import { heritageApi, vocabApi } from '@/lib/api';
import { ApiError } from '@/lib/api/errors';
import { ErrorState } from '@/components/ui/empty-state';
import { HeritageTable } from './heritage-table';

interface HeritagePageProps {
  readonly searchParams?: Readonly<{
    kind?: string;
    country?: string;
    status?: string;
    search?: string;
    offset?: string;
  }>;
}

export default async function HeritagePage({
  searchParams,
}: HeritagePageProps): Promise<JSX.Element> {
  const t = await getTranslations('heritage');
  const tCommon = await getTranslations('common');

  const limit = 20;
  const offset = Math.max(0, Number(searchParams?.offset ?? 0) || 0);

  const [page, kinds, regions] = await Promise.all([
    heritageApi
      .listHeritage({
        kind: searchParams?.kind,
        country: searchParams?.country,
        status: searchParams?.status,
        search: searchParams?.search,
        limit,
        offset,
      })
      .catch((cause: unknown) => cause as Error),
    vocabApi.getVocab('heritage_kinds').catch(() => null),
    vocabApi.getVocab('residency_regions').catch(() => null),
  ]);

  return (
    <PermissionGuard
      permission={PERMISSIONS.HERITAGE_READ}
      fallback={<AccessDenied />}
    >
      <PageHeader
        title={t('title')}
        subtitle={t('subtitle')}
        actions={
          <Button asChild>
            <Link href="/heritage/new">
              <Plus className="h-4 w-4" />
              {t('newEntry')}
            </Link>
          </Button>
        }
      />
      {page instanceof ApiError ? (
        <ErrorState title={tCommon('errorTitle')} message={page.message} />
      ) : page instanceof Error ? (
        <ErrorState title={tCommon('errorTitle')} message={page.message} />
      ) : (
        <HeritageTable
          page={page}
          limit={limit}
          offset={offset}
          initialFilters={{
            kind: searchParams?.kind ?? '',
            country: searchParams?.country ?? '',
            status: searchParams?.status ?? '',
            search: searchParams?.search ?? '',
          }}
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
      )}
    </PermissionGuard>
  );
}
