import { Card, CardContent } from '@/components/ui/card';
import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';

export default async function AiModelsPage(): Promise<JSX.Element> {
  return (
    <PermissionGuard
      permission={PERMISSIONS.AI_MODELS_READ}
      fallback={<AccessDenied />}
    >
      <PageHeader
        title="AI models"
        subtitle="Vision, TTS, translation, LLM — provider matrix + fallback chains."
      />
      <Card>
        <CardContent className="py-12 text-center text-sm text-muted-foreground">
          Per Roadmap admin panel imkoniyatlari: choose which model serves
          each domain, set temperature / prompt presets, and order the
          fallback chain. Wired once the AI inference service is reachable.
        </CardContent>
      </Card>
    </PermissionGuard>
  );
}
