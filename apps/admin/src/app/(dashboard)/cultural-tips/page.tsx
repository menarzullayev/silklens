import type { Metadata } from 'next';
import { Globe } from 'lucide-react';

import { apiFetch } from '@/lib/api/client';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { CulturalTip } from '@/types/api';

export const metadata: Metadata = {
  title: 'Cultural Tips',
};

// SILK-0159: Cultural tips page — reads from GET /v1/cultural-tips.
// Tips are grouped by context for easier scanning.

const SEVERITY_VARIANT: Record<
  CulturalTip['severity'],
  'default' | 'secondary' | 'destructive' | 'outline'
> = {
  info: 'secondary',
  warning: 'outline',
  critical: 'destructive',
};

export default async function CulturalTipsPage(): Promise<JSX.Element> {
  let tips: CulturalTip[] = [];
  try {
    const data = await apiFetch<CulturalTip[]>({
      path: '/v1/cultural-tips',
      query: { country_code: 'UZ', language: 'en' },
      anonymous: true,
    });
    tips = Array.isArray(data) ? data : [];
  } catch {
    // Endpoint may not be deployed yet — degrade gracefully.
  }

  // Group by context for display.
  const grouped = tips.reduce<Record<string, CulturalTip[]>>((acc, tip) => {
    const key = tip.context ?? 'general';
    if (!acc[key]) acc[key] = [];
    acc[key].push(tip);
    return acc;
  }, {});

  const contexts = Object.keys(grouped).sort();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Cultural Tips"
        subtitle="Cultural guidance for travellers visiting heritage sites"
      />

      {tips.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Globe className="h-4 w-4" aria-hidden />
              No cultural tips found. Ensure the backend has seed data for country code
              &ldquo;UZ&rdquo;.
            </div>
          </CardContent>
        </Card>
      ) : (
        contexts.map((context) => (
          <Card key={context}>
            <CardHeader>
              <CardTitle className="capitalize">{context.replace(/_/g, ' ')}</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {grouped[context]?.map((tip) => (
                  <div key={tip.id} className="rounded-lg border p-4">
                    <div className="mb-1 flex items-start justify-between gap-2">
                      <p className="font-medium">{tip.title}</p>
                      <div className="flex shrink-0 gap-1.5">
                        <Badge variant="outline">{tip.kind}</Badge>
                        <Badge variant={SEVERITY_VARIANT[tip.severity]}>{tip.severity}</Badge>
                      </div>
                    </div>
                    <p className="whitespace-pre-line text-sm text-muted-foreground">
                      {tip.body_md}
                    </p>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>
        ))
      )}
    </div>
  );
}
