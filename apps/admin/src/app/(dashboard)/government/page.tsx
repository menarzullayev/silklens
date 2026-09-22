import type { Metadata } from 'next';
import { Building2 } from 'lucide-react';

import { apiFetch } from '@/lib/api/client';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { GovernmentInfo } from '@/types/api';

export const metadata: Metadata = {
  title: 'Government Info',
};

// SILK-0160: Government information page — reads from GET /v1/government.
// Displays country-scoped government regulations, visa requirements, and
// official notices relevant to heritage travellers.

const KIND_VARIANT: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  regulation: 'default',
  visa: 'secondary',
  notice: 'outline',
  advisory: 'destructive',
};

export default async function GovernmentPage(): Promise<JSX.Element> {
  let items: GovernmentInfo[] = [];
  try {
    const data = await apiFetch<GovernmentInfo[]>({
      path: '/v1/government',
      query: { country_code: 'UZ', language: 'en' },
      anonymous: true,
    });
    items = Array.isArray(data) ? data : [];
  } catch {
    // Endpoint may not be deployed yet — degrade gracefully.
  }

  // Group by kind for easier scanning.
  const grouped = items.reduce<Record<string, GovernmentInfo[]>>((acc, item) => {
    const key = item.kind ?? 'general';
    if (!acc[key]) acc[key] = [];
    acc[key].push(item);
    return acc;
  }, {});

  const kinds = Object.keys(grouped).sort();

  return (
    <div className="space-y-6">
      <PageHeader
        title="Government Information"
        subtitle="Official regulations, visa requirements, and travel notices for Uzbekistan"
      />

      {items.length === 0 ? (
        <Card>
          <CardContent className="pt-6">
            <div className="flex items-center gap-3 text-sm text-muted-foreground">
              <Building2 className="h-4 w-4" aria-hidden />
              No government information found. Ensure the backend has seed data for country code
              &ldquo;UZ&rdquo;.
            </div>
          </CardContent>
        </Card>
      ) : (
        kinds.map((kind) => (
          <Card key={kind}>
            <CardHeader>
              <CardTitle className="flex items-center gap-2 capitalize">
                <Building2 className="h-4 w-4" aria-hidden />
                {kind.replace(/_/g, ' ')}
              </CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-3">
                {grouped[kind]?.map((item) => (
                  <div key={item.id} className="rounded-lg border p-4">
                    <div className="mb-2 flex items-start justify-between gap-2">
                      <p className="font-medium">{item.title}</p>
                      <div className="flex shrink-0 gap-1.5">
                        <Badge variant={KIND_VARIANT[item.kind] ?? 'outline'}>
                          {item.kind}
                        </Badge>
                        {item.effective_date && (
                          <Badge variant="outline" className="font-mono text-xs">
                            {item.effective_date}
                          </Badge>
                        )}
                      </div>
                    </div>
                    <p className="whitespace-pre-line text-sm text-muted-foreground">
                      {item.body_md}
                    </p>
                    {item.source_url ? (
                      <a
                        href={item.source_url}
                        target="_blank"
                        rel="noopener noreferrer"
                        className="mt-2 block text-xs text-primary hover:underline"
                      >
                        Source →
                      </a>
                    ) : null}
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
