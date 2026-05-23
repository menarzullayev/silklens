import { Building2, CreditCard, DollarSign, Package, TrendingUp } from 'lucide-react';

import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';
import { Badge } from '@/components/ui/badge';
import { EmptyState } from '@/components/ui/empty-state';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '@/components/ui/table';
import { billingApi, analyticsApi } from '@/lib/api';

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

function resolveName(
  name: billingApi.I18nString | string | undefined,
  slug: string,
): string {
  if (!name) return slug;
  if (typeof name === 'string') return name;
  return name.en ?? name.uz ?? name.ru ?? slug;
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
    return String(iso);
  }
}

function resellerStatusVariant(
  status: string,
): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'approved':
      return 'default';
    case 'pending':
      return 'secondary';
    case 'rejected':
      return 'destructive';
    default:
      return 'outline';
  }
}

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------

async function fetchData(): Promise<{
  plans: readonly billingApi.BillingPlan[];
  traction: analyticsApi.TractionData;
  resellerApplications: readonly billingApi.ResellerApplication[];
  resellerTotal: number;
}> {
  const [plansResult, tractionResult, resellerResult] =
    await Promise.allSettled([
      billingApi.getPlans('central_asia'),
      analyticsApi.getTractionData(),
      billingApi.getResellerApplications({ status: 'pending', limit: 10 }),
    ]);

  return {
    plans:
      plansResult.status === 'fulfilled'
        ? (plansResult.value.items ?? [])
        : [],
    traction:
      tractionResult.status === 'fulfilled' ? tractionResult.value : {},
    resellerApplications:
      resellerResult.status === 'fulfilled'
        ? (resellerResult.value.items ?? [])
        : [],
    resellerTotal:
      resellerResult.status === 'fulfilled'
        ? (resellerResult.value.total ?? 0)
        : 0,
  };
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function MonetizationPage(): Promise<JSX.Element> {
  const { plans, traction, resellerApplications, resellerTotal } =
    await fetchData();

  const revenue = [
    {
      label: 'ARR',
      value:
        typeof traction.arr_usd === 'number'
          ? `$${traction.arr_usd.toLocaleString()}`
          : '—',
      description: 'Annual Recurring Revenue',
      icon: TrendingUp,
    },
    {
      label: 'MRR',
      value:
        typeof (traction as { mrr_usd?: unknown }).mrr_usd === 'number'
          ? `$${(traction as { mrr_usd: number }).mrr_usd.toLocaleString()}`
          : '—',
      description: 'Monthly Recurring Revenue',
      icon: DollarSign,
    },
    {
      label: 'Active Subscriptions',
      value:
        (traction as { active_subscriptions?: unknown }).active_subscriptions ??
        '—',
      description: 'Paid seats across all plans',
      icon: CreditCard,
    },
    {
      label: 'Plans',
      value: plans.length,
      description: `${plans.filter((p) => p.is_active).length} active`,
      icon: Package,
    },
  ] as const;

  return (
    <PermissionGuard
      permission={PERMISSIONS.MONETIZATION_READ}
      fallback={<AccessDenied />}
    >
      <PageHeader
        title="Monetization"
        subtitle="Billing plans, subscriptions, and revenue overview"
      />

      {/* KPI row */}
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        {revenue.map((r) => {
          const Icon = r.icon;
          return (
            <Card key={r.label}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {r.label}
                </CardTitle>
                <Icon aria-hidden className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{String(r.value)}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {r.description}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
        {/* Billing plans table */}
        <Card>
          <CardHeader>
            <CardTitle className="text-base">
              Billing Plans ({plans.length})
            </CardTitle>
            <CardDescription>
              Managed via{' '}
              <strong>System Settings &rarr; Billing</strong>. Pricing zones:
              central_asia, eu, global.
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {plans.length === 0 ? (
              <div className="px-6 pb-6">
                <p className="text-sm text-muted-foreground">
                  No plans returned. The API may require auth or no plans are
                  configured yet.
                </p>
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Plan</TableHead>
                    <TableHead className="w-20">Slug</TableHead>
                    <TableHead className="w-24 text-right">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {plans.map((plan) => {
                    const name = resolveName(plan.display_name, plan.slug);
                    return (
                      <TableRow key={plan.slug}>
                        <TableCell className="font-medium">{name}</TableCell>
                        <TableCell className="font-mono text-xs text-muted-foreground">
                          {plan.slug}
                        </TableCell>
                        <TableCell className="text-right">
                          <Badge
                            variant={plan.is_active ? 'default' : 'secondary'}
                          >
                            {plan.is_active ? 'Active' : 'Inactive'}
                          </Badge>
                        </TableCell>
                      </TableRow>
                    );
                  })}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Reseller applications */}
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              <Building2 aria-hidden className="h-5 w-5" />
              Reseller Applications
              {resellerTotal > 0 && (
                <Badge variant="secondary" className="ml-auto">
                  {resellerTotal} pending
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              Partners applying for the white-label reseller programme
              (Project-Decisions §50).
            </CardDescription>
          </CardHeader>
          <CardContent className="p-0">
            {resellerApplications.length === 0 ? (
              <div className="px-6 pb-8">
                <EmptyState
                  icon={Building2}
                  title="No pending applications"
                  description="Reseller partner applications will appear here when submitted. The endpoint GET /v1/admin/reseller/applications is wired and ready."
                  className="border-0 shadow-none"
                />
              </div>
            ) : (
              <Table>
                <TableHeader>
                  <TableRow>
                    <TableHead>Company</TableHead>
                    <TableHead>Contact</TableHead>
                    <TableHead className="w-28">Applied</TableHead>
                    <TableHead className="w-24 text-right">Status</TableHead>
                  </TableRow>
                </TableHeader>
                <TableBody>
                  {resellerApplications.map((app) => (
                    <TableRow key={app.id}>
                      <TableCell className="font-medium">
                        {app.company_name}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {app.contact_email}
                      </TableCell>
                      <TableCell className="text-sm text-muted-foreground">
                        {formatDate(app.created_at)}
                      </TableCell>
                      <TableCell className="text-right">
                        <Badge variant={resellerStatusVariant(app.status)}>
                          {app.status}
                        </Badge>
                      </TableCell>
                    </TableRow>
                  ))}
                </TableBody>
              </Table>
            )}
          </CardContent>
        </Card>

        {/* Revenue note */}
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle className="text-sm font-medium text-muted-foreground">
              Revenue Data
            </CardTitle>
          </CardHeader>
          <CardContent>
            <p className="text-sm text-muted-foreground">
              Real-time MRR/ARR figures are sourced from Stripe and surfaced
              via the investor traction endpoint. Until Stripe integration is
              configured (FAZA 7), the values above show{' '}
              <strong>&ldquo;&mdash;&rdquo;</strong>. Manage billing from the
              Stripe Dashboard or via{' '}
              <strong>System Settings &rarr; Billing</strong>.
            </p>
          </CardContent>
        </Card>
      </div>
    </PermissionGuard>
  );
}
