import { Card, CardContent } from '@/components/ui/card';
import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';

/**
 * Super-admin only — the only place to provision new white-label tenants
 * (Project-Decisions §50). All other admin surfaces are tenant-scoped via
 * the topbar tenant switcher and `X-Tenant-Id` header.
 */
export default async function TenantsPage(): Promise<JSX.Element> {
  return (
    <PermissionGuard
      permission={PERMISSIONS.TENANTS_MANAGE}
      fallback={<AccessDenied />}
    >
      <PageHeader
        title="Tenants"
        subtitle="Super-admin: provision white-label tenants, set revenue shares, attach domains."
      />
      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          Tenant lifecycle (active / suspended / archived) and reseller
          hierarchies land with the Monetization router.
        </CardContent>
      </Card>
    </PermissionGuard>
  );
}
