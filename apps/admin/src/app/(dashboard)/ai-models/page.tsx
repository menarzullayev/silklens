import { getTranslations } from 'next-intl/server';

import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';
import { aiApi } from '@/lib/api';
import { ApiError } from '@/lib/api/errors';
import { ErrorState } from '@/components/ui/empty-state';
import { ModelsTable } from './models-table';
import { ChainsView } from './chains-view';

export default async function AiModelsPage(): Promise<JSX.Element> {
  const t = await getTranslations('aiModels');
  const tCommon = await getTranslations('common');

  const [models, chains] = await Promise.all([
    aiApi.listAiModels().catch((cause: unknown) => cause),
    aiApi.listAiFallbackChains().catch((cause: unknown) => cause),
  ]);

  return (
    <PermissionGuard
      permission={PERMISSIONS.AI_MODELS_READ}
      fallback={<AccessDenied />}
    >
      <PageHeader title={t('title')} subtitle={t('subtitle')} />
      <Tabs defaultValue="models" className="space-y-4">
        <TabsList>
          <TabsTrigger value="models">{t('tabModels')}</TabsTrigger>
          <TabsTrigger value="chains">{t('tabChains')}</TabsTrigger>
          <TabsTrigger value="usage">{t('tabUsage')}</TabsTrigger>
        </TabsList>
        <TabsContent value="models">
          {models instanceof ApiError ? (
            <ErrorState title={t('errorTitle')} message={models.message} />
          ) : models instanceof Error ? (
            <ErrorState title={t('errorTitle')} message={models.message} />
          ) : (
            <ModelsTable models={models} />
          )}
        </TabsContent>
        <TabsContent value="chains">
          {chains instanceof ApiError ? (
            <ErrorState title={t('errorTitle')} message={chains.message} />
          ) : chains instanceof Error ? (
            <ErrorState title={t('errorTitle')} message={chains.message} />
          ) : (
            <ChainsView chains={chains} />
          )}
        </TabsContent>
        <TabsContent value="usage">
          <Card>
            <CardContent className="py-12 text-center text-sm text-muted-foreground">
              <Badge variant="secondary">{tCommon('comingSoon')}</Badge>
              <p className="mt-2">{t('usageHint')}</p>
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </PermissionGuard>
  );
}
