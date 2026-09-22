import { notFound } from 'next/navigation';
import { getTranslations } from 'next-intl/server';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';
import { heritageApi, vocabApi, reviewsApi } from '@/lib/api';
import { NotFoundError } from '@/lib/api/errors';
import { HeritageForm } from '../heritage-form';
import { TransitionBar } from './transition-bar';
import { AliasesPanel } from './aliases-panel';
import { TranslationsMatrix } from './translations-matrix';
import { RevisionsTimeline } from './revisions-timeline';

interface DetailPageProps {
  readonly params: Promise<{ readonly pub_id: string }>;
}

function pickName(name: Record<string, string>): string {
  return name.en ?? name.uz ?? Object.values(name)[0] ?? '—';
}

export default async function HeritageDetailPage({
  params,
}: DetailPageProps): Promise<JSX.Element> {
  const t = await getTranslations('heritage');
  const { pub_id: pubId } = await params;

  const heritage = await heritageApi
    .getHeritage(pubId)
    .catch((cause: unknown) => {
      if (cause instanceof NotFoundError) return null;
      throw cause;
    });
  if (!heritage) notFound();

  const [kinds, regions, revisions, reviews] = await Promise.all([
    vocabApi.getVocab('heritage_kinds').catch(() => null),
    vocabApi.getVocab('residency_regions').catch(() => null),
    heritageApi.listHeritageRevisions(pubId, { limit: 20 }).catch(() => null),
    reviewsApi.listHeritageReviews(pubId, { limit: 5 }).catch(() => null),
  ]);

  return (
    <PermissionGuard
      permission={PERMISSIONS.HERITAGE_READ}
      fallback={<AccessDenied />}
    >
      <PageHeader
        title={pickName(heritage.name)}
        subtitle={`pub_id: ${heritage.pub_id} · rev ${heritage.revision}`}
        actions={
          <div className="flex items-center gap-2">
            <Badge variant="outline" className="capitalize">
              {heritage.kind_slug.replace(/_/g, ' ')}
            </Badge>
            <Badge variant="secondary" className="capitalize">
              {heritage.status}
            </Badge>
          </div>
        }
      />
      <TransitionBar pubId={heritage.pub_id} status={heritage.status} />
      <Tabs defaultValue="overview" className="mt-4">
        <TabsList>
          <TabsTrigger value="overview">{t('tabOverview')}</TabsTrigger>
          <TabsTrigger value="translations">{t('tabTranslations')}</TabsTrigger>
          <TabsTrigger value="aliases">{t('tabAliases')}</TabsTrigger>
          <TabsTrigger value="revisions">{t('tabRevisions')}</TabsTrigger>
          <TabsTrigger value="reviews">{t('tabReviews')}</TabsTrigger>
        </TabsList>
        <TabsContent value="overview">
          <HeritageForm
            mode="edit"
            initial={heritage}
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
        </TabsContent>
        <TabsContent value="translations">
          <TranslationsMatrix heritage={heritage} />
        </TabsContent>
        <TabsContent value="aliases">
          <AliasesPanel pubId={heritage.pub_id} />
        </TabsContent>
        <TabsContent value="revisions">
          <RevisionsTimeline revisions={revisions?.items ?? []} />
        </TabsContent>
        <TabsContent value="reviews">
          <Card>
            <CardHeader>
              <CardTitle>Latest reviews</CardTitle>
            </CardHeader>
            <CardContent>
              {reviews && reviews.items.length > 0 ? (
                <ul className="divide-y">
                  {reviews.items.map((r) => (
                    <li key={r.id} className="py-3 text-sm">
                      <div className="flex items-center justify-between">
                        <span className="font-medium">★ {r.rating}/5</span>
                        <Badge variant="outline" className="capitalize">
                          {r.status}
                        </Badge>
                      </div>
                      {r.body ? (
                        <p className="mt-1 text-muted-foreground">{r.body}</p>
                      ) : null}
                    </li>
                  ))}
                </ul>
              ) : (
                <p className="text-sm text-muted-foreground">
                  No reviews yet for this heritage.
                </p>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </PermissionGuard>
  );
}
