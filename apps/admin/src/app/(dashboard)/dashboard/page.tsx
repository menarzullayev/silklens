import { getTranslations } from 'next-intl/server';
import { BarChart3, Eye, Sparkles, UserCheck, Users } from 'lucide-react';

import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';
import { formatMoney } from '@/lib/utils';

interface MetricCardProps {
  readonly label: string;
  readonly value: string;
  readonly icon: typeof Users;
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

export default async function DashboardOverviewPage(): Promise<JSX.Element> {
  const t = await getTranslations('dashboard');

  // TODO(analytics): replace with `apiFetch('/admin/analytics/overview')`.
  const metrics = {
    activeUsers24h: 1284,
    activeUsers7d: 8930,
    heritageViews24h: 17_402,
    premium: 312,
    revenueMtd: 4382.91,
  };

  return (
    <PermissionGuard
      permission={PERMISSIONS.ANALYTICS_READ}
      fallback={<AccessDenied />}
    >
      <PageHeader title={t('title')} subtitle={t('subtitle')} />
      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
        <MetricCard
          label={t('metricUsers24h')}
          value={metrics.activeUsers24h.toLocaleString()}
          icon={Users}
        />
        <MetricCard
          label={t('metricUsers7d')}
          value={metrics.activeUsers7d.toLocaleString()}
          icon={UserCheck}
        />
        <MetricCard
          label={t('metricHeritageViews')}
          value={metrics.heritageViews24h.toLocaleString()}
          icon={Eye}
        />
        <MetricCard
          label={t('metricPremium')}
          value={metrics.premium.toLocaleString()}
          icon={Sparkles}
        />
        <MetricCard
          label={t('metricRevenueMtd')}
          value={formatMoney(metrics.revenueMtd)}
          icon={BarChart3}
        />
      </div>
    </PermissionGuard>
  );
}
