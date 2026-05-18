import { Card, CardContent } from '@/components/ui/card';
import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';

export default async function ModerationPage(): Promise<JSX.Element> {
  return (
    <PermissionGuard
      permission={PERMISSIONS.MODERATION_READ}
      fallback={<AccessDenied />}
    >
      <PageHeader
        title="Moderation"
        subtitle="UGC queue with AI-scored triage (Project-Decisions §43)."
      />
      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          Hooked up once the social/UGC routers from architecture §05 land.
        </CardContent>
      </Card>
    </PermissionGuard>
  );
}
