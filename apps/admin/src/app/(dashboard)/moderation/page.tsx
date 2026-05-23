import {
  AlertTriangle,
  CheckCircle,
  Clock,
  ShieldCheck,
} from 'lucide-react';

import { PageHeader } from '@/components/layout/page-header';
import { PermissionGuard } from '@/components/rbac/permission-guard';
import { AccessDenied } from '@/components/rbac/access-denied';
import { PERMISSIONS } from '@/lib/rbac/permissions';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { moderationApi } from '@/lib/api';
import type { HeritageOut } from '@/types/api';
import { ModerationTable } from './moderation-table';

// ---------------------------------------------------------------------------
// Data fetching
// ---------------------------------------------------------------------------

async function fetchQueue(): Promise<{
  items: HeritageOut[];
  total: number;
}> {
  try {
    const page = await moderationApi.getModerationQueue({ limit: 20 });
    return {
      items: [...page.items] as HeritageOut[],
      total: page.total,
    };
  } catch {
    return { items: [], total: 0 };
  }
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default async function ModerationPage(): Promise<JSX.Element> {
  const { items, total } = await fetchQueue();

  const queueStats = [
    {
      label: 'Pending Reviews',
      count: total,
      description: 'Awaiting moderation',
      icon: Clock,
    },
    {
      label: 'Flagged Content',
      count: 0,
      description: 'User-reported items',
      icon: AlertTriangle,
    },
    {
      label: 'Auto-flagged',
      count: 0,
      description: 'AI moderation queue',
      icon: ShieldCheck,
    },
    {
      label: 'Resolved Today',
      count: 0,
      description: 'Cleared items',
      icon: CheckCircle,
    },
  ] as const;

  return (
    <PermissionGuard
      permission={PERMISSIONS.MODERATION_READ}
      fallback={<AccessDenied />}
    >
      <PageHeader
        title="Moderation"
        subtitle="Review heritage submissions and flagged content"
      />

      {/* Queue counters */}
      <div className="mb-6 grid grid-cols-2 gap-4 md:grid-cols-4">
        {queueStats.map((q) => {
          const Icon = q.icon;
          return (
            <Card key={q.label}>
              <CardContent className="pt-6">
                <div className="flex items-center justify-between">
                  <div>
                    <p className="text-sm text-muted-foreground">{q.label}</p>
                    <p className="mt-1 text-3xl font-bold">{q.count}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      {q.description}
                    </p>
                  </div>
                  <Icon
                    aria-hidden
                    className="h-8 w-8 text-muted-foreground opacity-50"
                  />
                </div>
              </CardContent>
            </Card>
          );
        })}
      </div>

      {/* Heritage review queue */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-base">
            <ShieldCheck aria-hidden className="h-5 w-5" />
            Heritage Review Queue
          </CardTitle>
        </CardHeader>
        <CardContent>
          <ModerationTable items={items} total={total} />
        </CardContent>
      </Card>
    </PermissionGuard>
  );
}
