import { Card, CardContent } from '@/components/ui/card';
import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';

export default async function UsersPage(): Promise<JSX.Element> {
  return (
    <PermissionGuard
      permission={PERMISSIONS.USERS_READ}
      fallback={<AccessDenied />}
    >
      <PageHeader
        title="Users"
        subtitle="Roles, scopes, premium status, GDPR holds."
      />
      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          User directory and role-grant flows arrive with the Identity service
          (HANDOFF pickup #3). RBAC and consent purposes already match the
          contracts in <code>docs/architecture/02-identity-rbac-gdpr.md</code>.
        </CardContent>
      </Card>
    </PermissionGuard>
  );
}
