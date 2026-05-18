import { Plus } from 'lucide-react';

import { Button } from '@/components/ui/button';
import { Card, CardContent } from '@/components/ui/card';
import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';

export default async function HeritagePage(): Promise<JSX.Element> {
  return (
    <PermissionGuard
      permission={PERMISSIONS.HERITAGE_READ}
      fallback={<AccessDenied />}
    >
      <PageHeader
        title="Heritage"
        subtitle="Manage monuments, sites, and AI-generated descriptions."
        actions={
          <Button>
            <Plus className="h-4 w-4" />
            New heritage entry
          </Button>
        }
      />
      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          Heritage CRUD lands once the FastAPI heritage router ships (HANDOFF
          pickup #4). This view will list, search, and filter the
          ~280-table heritage domain via the canonical{' '}
          <code>DataTable</code> component.
        </CardContent>
      </Card>
    </PermissionGuard>
  );
}
