import { Globe, Shield, UserCheck, Users } from 'lucide-react';

import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';
import { EmptyState } from '@/components/ui/empty-state';
import { Badge } from '@/components/ui/badge';
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
  CardDescription,
} from '@/components/ui/card';
import { analyticsApi } from '@/lib/api';

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------

async function fetchTraction(): Promise<analyticsApi.TractionData> {
  try {
    return await analyticsApi.getTractionData();
  } catch {
    return {};
  }
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function UsersPage(): Promise<JSX.Element> {
  const traction = await fetchTraction();

  const stats = [
    {
      label: 'Total Users',
      value: traction.total_users ?? '—',
      description: 'All-time registrations',
      icon: Users,
    },
    {
      label: 'Verified',
      value: traction.verified_users ?? '—',
      description: 'Email-confirmed accounts',
      icon: UserCheck,
    },
    {
      label: 'Monthly Active',
      value: traction.mau ?? '—',
      description: 'Last 30 days',
      icon: Globe,
    },
    {
      label: 'Staff / Admins',
      value: '—',
      description: 'super_admin + staff trust tiers',
      icon: Shield,
    },
  ] as const;

  return (
    <PermissionGuard
      permission={PERMISSIONS.USERS_READ}
      fallback={<AccessDenied />}
    >
      <PageHeader
        title="Users"
        subtitle="Platform users, roles, and trust-tier controls"
      />

      {/* Stats row (sourced from investor traction endpoint) */}
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        {stats.map((s) => {
          const Icon = s.icon;
          return (
            <Card key={s.label}>
              <CardHeader className="flex flex-row items-center justify-between pb-2">
                <CardTitle className="text-sm font-medium text-muted-foreground">
                  {s.label}
                </CardTitle>
                <Icon aria-hidden className="h-4 w-4 text-muted-foreground" />
              </CardHeader>
              <CardContent>
                <p className="text-2xl font-bold">{String(s.value)}</p>
                <p className="mt-1 text-xs text-muted-foreground">
                  {s.description}
                </p>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* What this page WILL contain */}
      <div className="grid grid-cols-1 gap-6 md:grid-cols-2">
        <EmptyState
          icon={Users}
          title="User Management"
          description="Search, filter by trust-tier, view session history, ban/unban, and assign roles. Requires GET /v1/admin/users — available in v0.4."
          action={<Badge variant="secondary">Coming in v0.4</Badge>}
        />

        <Card>
          <CardHeader>
            <CardTitle className="text-sm font-medium">Trust Tiers</CardTitle>
            <CardDescription>
              The platform uses a 5-level trust system. Each tier gates
              different API permissions.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-2 text-sm">
            {[
              { tier: 'system_actor', label: 'System', note: 'Internal automation' },
              { tier: 'super_admin', label: 'Super Admin', note: 'Full platform access' },
              { tier: 'staff', label: 'Staff', note: 'Content moderation + analytics' },
              { tier: 'verified', label: 'Verified', note: 'Confirmed email users' },
              { tier: 'authenticated', label: 'Authenticated', note: 'Registered, unverified' },
            ].map((t) => (
              <div
                key={t.tier}
                className="flex items-center justify-between rounded-md border px-3 py-2"
              >
                <div>
                  <span className="font-mono text-xs text-muted-foreground">
                    {t.tier}
                  </span>
                  <span className="ml-2 font-medium">{t.label}</span>
                </div>
                <span className="text-xs text-muted-foreground">{t.note}</span>
              </div>
            ))}
          </CardContent>
        </Card>
      </div>
    </PermissionGuard>
  );
}
