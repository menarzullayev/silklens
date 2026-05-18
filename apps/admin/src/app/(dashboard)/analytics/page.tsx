import { Card, CardContent } from '@/components/ui/card';
import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';

export default async function AnalyticsPage(): Promise<JSX.Element> {
  return (
    <PermissionGuard
      permission={PERMISSIONS.ANALYTICS_READ}
      fallback={<AccessDenied />}
    >
      <PageHeader
        title="Analytics"
        subtitle="Real-time + cohort metrics from the analytics warehouse."
      />
      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          Recharts dashboards land once the events pipeline (architecture §07)
          is reachable from this admin panel.
        </CardContent>
      </Card>
    </PermissionGuard>
  );
}
