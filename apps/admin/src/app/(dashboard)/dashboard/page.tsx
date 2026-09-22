import { getTranslations } from 'next-intl/server';
import { Activity, Box, Building2, Sparkles, Star } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';
import { heritageApi, tenantsApi } from '@/lib/api';
import { ApiError } from '@/lib/api/errors';

interface MetricCardProps {
  readonly label: string;
  readonly value: string;
  readonly icon: typeof Box;
  readonly trend?: string;
}

function MetricCard({ label, value, icon: Icon, trend }: MetricCardProps): JSX.Element {
  return (
    <Card>
      <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
        <CardTitle className="text-sm font-medium text-muted-foreground">
          {label}
        </CardTitle>
        <Icon className="h-4 w-4 text-muted-foreground" aria-hidden />
      </CardHeader>
      <CardContent>
        <div className="text-2xl font-semibold tracking-tight">{value}</div>
        {trend ? (
          <p className="mt-1 text-xs text-muted-foreground">{trend}</p>
        ) : null}
      </CardContent>
    </Card>
  );
}

interface CountResult {
  readonly value: string;
  readonly trend?: string;
}

async function safeHeritageTotal(): Promise<CountResult> {
  try {
    const page = await heritageApi.listHeritage({ limit: 1 });
    return { value: page.total.toLocaleString() };
  } catch (cause) {
    return { value: '—', trend: errorTrend(cause) };
  }
}

async function safePublishedTotal(): Promise<CountResult> {
  try {
    const page = await heritageApi.listHeritage({ limit: 1, status: 'published' });
    return { value: page.total.toLocaleString() };
  } catch (cause) {
    return { value: '—', trend: errorTrend(cause) };
  }
}

async function safeTenantTotal(): Promise<CountResult> {
  try {
    const page = await tenantsApi.listTenants({ limit: 1 });
    return { value: page.total.toLocaleString() };
  } catch (cause) {
    return { value: '—', trend: errorTrend(cause) };
  }
}

function errorTrend(cause: unknown): string {
  if (cause instanceof ApiError) return `API error (${cause.status})`;
  return 'API unreachable';
}

export default async function DashboardOverviewPage(): Promise<JSX.Element> {
  const t = await getTranslations('dashboard');
  const tCommon = await getTranslations('common');

  // Fire counts in parallel. Each promise traps its own errors so a single
  // backend hiccup doesn't fail the whole page.
  const [heritageTotal, publishedTotal, tenantTotal] = await Promise.all([
    safeHeritageTotal(),
    safePublishedTotal(),
    safeTenantTotal(),
  ]);

  return (
    <PermissionGuard
      permission={PERMISSIONS.ANALYTICS_READ}
      fallback={<AccessDenied />}
    >
      <PageHeader title={t('title')} subtitle={t('subtitle')} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <MetricCard
          label={t('metricHeritageTotal')}
          value={heritageTotal.value}
          trend={heritageTotal.trend}
          icon={Box}
        />
        <MetricCard
          label={t('metricHeritagePublished')}
          value={publishedTotal.value}
          trend={publishedTotal.trend}
          icon={Star}
        />
        <MetricCard
          label={t('metricTenants')}
          value={tenantTotal.value}
          trend={tenantTotal.trend}
          icon={Building2}
        />
        <MetricCard
          label={t('metricAiCalls')}
          value="—"
          trend={tCommon('comingSoon')}
          icon={Sparkles}
        />
      </div>

      <div className="mt-6 grid gap-4 lg:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Activity className="h-4 w-4 text-muted-foreground" aria-hidden />
              {t('recentActivity')}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <Badge variant="secondary">{tCommon('comingSoon')}</Badge>
            <p className="mt-2">{t('recentActivityHint')}</p>
          </CardContent>
        </Card>
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-sm">
              <Sparkles className="h-4 w-4 text-muted-foreground" aria-hidden />
              {t('aiPerformance')}
            </CardTitle>
          </CardHeader>
          <CardContent className="text-sm text-muted-foreground">
            <Badge variant="secondary">{tCommon('comingSoon')}</Badge>
            <p className="mt-2">{t('aiPerformanceHint')}</p>
          </CardContent>
        </Card>
      </div>
    </PermissionGuard>
  );
}
