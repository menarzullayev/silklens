import { Card, CardContent } from '@/components/ui/card';
import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';

export default async function MonetizationPage(): Promise<JSX.Element> {
  return (
    <PermissionGuard
      permission={PERMISSIONS.MONETIZATION_READ}
      fallback={<AccessDenied />}
    >
      <PageHeader
        title="Monetization"
        subtitle="Products, prices, pricing zones, dunning & affiliate splits."
      />
      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          Backed by architecture §06 (Monetization & Enterprise). Every row
          here is tenant-scoped — switch tenants from the topbar to drill in.
        </CardContent>
      </Card>
    </PermissionGuard>
  );
}
