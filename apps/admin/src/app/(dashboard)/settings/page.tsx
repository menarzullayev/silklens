import { Card, CardContent } from '@/components/ui/card';
import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';

export default async function SettingsPage(): Promise<JSX.Element> {
  return (
    <PermissionGuard
      permission={PERMISSIONS.SETTINGS_MANAGE}
      fallback={<AccessDenied />}
    >
      <PageHeader
        title="Settings"
        subtitle="System-wide configuration (feature flags, OAuth providers, controlled vocabularies)."
      />
      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          Backs the `system_settings`, `feature_flags`, `oauth_providers`, and
          `controlled_vocabularies` tables from HANDOFF migrations 0002–0010.
        </CardContent>
      </Card>
    </PermissionGuard>
  );
}
