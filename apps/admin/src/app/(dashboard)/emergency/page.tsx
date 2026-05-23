import type { Metadata } from 'next';
import { Phone } from 'lucide-react';

import { apiFetch } from '@/lib/api/client';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { EmergencyContact } from '@/types/api';

export const metadata: Metadata = {
  title: 'Emergency Contacts',
};

// SILK-0158: Emergency contacts page — reads from GET /v1/emergency.
// Requires system:settings permission (enforced at sidebar; layout
// already gates the whole dashboard behind an authenticated session).

export default async function EmergencyPage(): Promise<JSX.Element> {
  let contacts: EmergencyContact[] = [];
  try {
    const data = await apiFetch<EmergencyContact[]>({
      path: '/v1/emergency',
      query: { country_code: 'UZ', language: 'en' },
      anonymous: true,
    });
    contacts = Array.isArray(data) ? data : [];
  } catch {
    // Endpoint may not be deployed yet — degrade gracefully.
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Emergency Contacts"
        subtitle="Emergency contact directory for users in the field"
      />
      <Card>
        <CardHeader>
          <CardTitle>Uzbekistan Emergency Contacts ({contacts.length})</CardTitle>
        </CardHeader>
        <CardContent>
          {contacts.length === 0 ? (
            <p className="text-sm text-muted-foreground">
              No emergency contacts found. Ensure the backend has seed data for country code
              &ldquo;UZ&rdquo;.
            </p>
          ) : (
            <div className="space-y-2">
              {contacts.map((contact) => (
                <div
                  key={contact.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div className="flex items-center gap-3">
                    <Phone className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
                    <div>
                      <p className="font-medium">{contact.name}</p>
                      <p className="text-sm text-muted-foreground">
                        {contact.kind}
                        {contact.phone ? ` · ${contact.phone}` : ''}
                        {contact.phone_alt ? ` / ${contact.phone_alt}` : ''}
                      </p>
                      {contact.address ? (
                        <p className="text-xs text-muted-foreground">{contact.address}</p>
                      ) : null}
                    </div>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    {contact.languages_spoken.length > 0 && (
                      <Badge variant="outline" className="hidden sm:inline-flex">
                        {contact.languages_spoken.join(', ')}
                      </Badge>
                    )}
                    {contact.is_24h && <Badge variant="secondary">24/7</Badge>}
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
