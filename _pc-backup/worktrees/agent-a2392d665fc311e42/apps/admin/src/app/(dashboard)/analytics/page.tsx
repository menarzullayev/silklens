import {
  Brain,
  Database,
  Eye,
  Search,
  TrendingUp,
  Users,
  Clock,
} from 'lucide-react';

import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { analyticsApi } from '@/lib/api';
import type { HeritageOut } from '@/types/api';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function pickName(name: Record<string, string>): string {
  return name.en ?? name.uz ?? name.ru ?? Object.values(name)[0] ?? '—';
}

function statusVariant(
  status: string,
): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'published':
      return 'default';
    case 'review':
      return 'secondary';
    case 'rejected':
      return 'destructive';
    default:
      return 'outline';
  }
}

function formatDate(iso: string | null | undefined): string {
  if (!iso) return '—';
  try {
    return new Date(iso).toLocaleDateString('en-GB', {
      day: '2-digit',
      month: 'short',
      year: 'numeric',
    });
  } catch {
    return iso;
  }
}

// ---------------------------------------------------------------------------
// Placeholder top-search rows (real pipeline lands in FAZA 8)
// ---------------------------------------------------------------------------

const TOP_SEARCHES = [
  { query: 'Registan', count: '—', trend: '↑' },
  { query: 'Samarkand', count: '—', trend: '↑' },
  { query: 'Bukhara', count: '—', trend: '—' },
  { query: 'Khiva', count: '—', trend: '↑' },
  { query: 'Shah-i-Zinda', count: '—', trend: '—' },
] as const;

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------

async function fetchData(): Promise<{
  traction: analyticsApi.TractionData;
  heritageTotal: number;
  recentHeritage: readonly HeritageOut[];
}> {
  const [tractionResult, recentResult] = await Promise.allSettled([
    analyticsApi.getTractionData(),
    analyticsApi.getRecentHeritage(5),
  ]);

  const traction =
    tractionResult.status === 'fulfilled' ? tractionResult.value : {};
  const recentPage =
    recentResult.status === 'fulfilled' ? recentResult.value : null;

  return {
    traction,
    heritageTotal:
      recentPage?.total ?? (traction.heritage_count as number | undefined) ?? 0,
    recentHeritage: recentPage?.items ?? [],
  };
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function AnalyticsPage(): Promise<JSX.Element> {
  const { traction, heritageTotal, recentHeritage } = await fetchData();

  const kpis = [
    {
      label: 'Heritage Sites',
      value: heritageTotal > 0 ? heritageTotal : (traction.heritage_count ?? '—'),
      description: 'Total in catalogue',
      icon: Database,
    },
    {
      label: 'Monthly Active Users',
      value: traction.mau ?? '—',
      description: 'Last 30 days',
      icon: TrendingUp,
    },
    {
      label: 'Registered Users',
      value: traction.total_users ?? '—',
      description: 'All-time registrations',
      icon: Users,
    },
    {
      label: 'AI Requests',
      value: traction.ai_requests ?? '—',
      description: 'Vision + TTS + Chat',
      icon: Brain,
    },
  ] as const;

  return (
    <PermissionGuard
      permission={PERMISSIONS.ANALYTICS_READ}
      fallback={<AccessDenied />}
    >
      <PageHeader
        title="Analytics"
        subtitle="Platform metrics, usage statistics, and recent activity"
      />

      {/* KPI row */}
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <Card key={kpi.label}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {kpi.label}
                </CardTitle>
                <Icon aria-hidden className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{String(kpi.value)}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {kpi.description}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Top searches — placeholder until FAZA 8 search pipeline */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Search aria-hidden className="h-5 w-5" />
              Top Searches
            </CardTitle>
            <CardDescription>
              Real-time search analytics pipeline arrives in FAZA 8.
              Elasticsearch query-log aggregation is wired but not yet surfaced
              via API.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Query</TableHead>
                  <TableHead className="w-24 text-right">Count</TableHead>
                  <TableHead className="w-16 text-right">Trend</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {TOP_SEARCHES.map((row) => (
                  <TableRow key={row.query}>
                    <TableCell className="font-medium">{row.query}</TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {row.count}
                    </TableCell>
                    <TableCell className="text-right text-muted-foreground">
                      {row.trend}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>

        {/* Recent heritage activity */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Clock aria-hidden className="h-5 w-5" />
              Recent Heritage Activity
            </CardTitle>
            <CardDescription>
              Last 5 heritage entries by creation order.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {recentHeritage.length === 0 ? (
              <div className="py-8 text-center text-sm text-muted-foreground">
                No heritage entries found.
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Name</TableHead>
                    <TableHead className="w-28">Country</TableHead>
                    <TableHead className="w-28">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {recentHeritage.map((item) => (
                    <TableRow key={item.pub_id}>
                      <TableCell className="font-medium">
                        {pickName(item.name)}
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {item.country_code ?? '—'}
                      </TableCell>
                      <TableCell>
                        <Badge
                          variant={statusVariant(item.status)}
                          className="capitalize"
                        >
                          {item.status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Search engine info */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Eye aria-hidden className="h-5 w-5" />
              Search Engine
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Elasticsearch-backed, 5-language tiered indexing. Manage index
              health and reindex triggers from{' '}
              <strong>Feature Flags &rarr; Search</strong>. Heritage-views and
              AI-request counters will be available once the analytics event
              pipeline (Redpanda &rarr; ClickHouse) is deployed in FAZA 8.
            </p>
          </CardContent>
        </Card>
      </div>
    </PermissionGuard>
  );
}
