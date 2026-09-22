import type { Metadata } from 'next';

import { apiFetch } from '@/lib/api/client';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { LanguageOut } from '@/types/api';

export const metadata: Metadata = {
  title: 'Languages',
};

// SILK-0166: Language registry page — reads from GET /v1/public/languages.
// Displays the 7 configured platform languages with BCP-47 tag, endonym,
// exonym, RTL flag and active status.

export default async function LanguagesPage(): Promise<JSX.Element> {
  let languages: LanguageOut[] = [];
  try {
    const data = await apiFetch<LanguageOut[]>({
      path: '/v1/public/languages',
      anonymous: true,
    });
    languages = Array.isArray(data) ? data : [];
  } catch {
    // Endpoint may not be deployed yet — degrade gracefully.
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Languages"
        subtitle="Supported language registry — BCP-47 codes, scripts, and active status"
      />
      <Card>
        <CardContent className="pt-6">
          {languages.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No languages configured. The backend may not yet expose{' '}
              <code className="font-mono text-xs">GET /v1/public/languages</code>.
            </p>
          ) : (
            <div className="space-y-2">
              {languages.map((lang) => (
                <div
                  key={lang.bcp47_tag}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div>
                    <p className="font-medium">
                      {lang.endonym}{' '}
                      <span className="text-muted-foreground">({lang.exonym_en})</span>
                    </p>
                    <p className="text-xs text-muted-foreground">
                      BCP-47: <code className="font-mono">{lang.bcp47_tag}</code>
                    </p>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    {lang.is_rtl && <Badge variant="outline">RTL</Badge>}
                    <Badge variant={lang.is_active ? 'default' : 'secondary'}>
                      {lang.is_active ? 'Active' : 'Inactive'}
                    </Badge>
                  </div>
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
