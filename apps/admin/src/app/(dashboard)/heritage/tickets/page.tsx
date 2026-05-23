import type { Metadata } from 'next';
import Link from 'next/link';
import { Ticket as TicketIcon } from 'lucide-react';

import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Button } from '@/components/ui/button';

export const metadata: Metadata = {
  title: 'Ticket Types',
};

// SILK-0163: Ticket types management page.
// Ticket types are scoped to individual heritage sites. Navigate to a site's
// detail page to create or edit ticket types for it.

export default function HeritageTicketsPage(): JSX.Element {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Ticket Types"
        subtitle="Entry ticket configuration for heritage sites"
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <TicketIcon className="h-5 w-5" aria-hidden />
            Per-site ticket management
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <p className="text-sm text-muted-foreground">
            Ticket types are managed per heritage site. Each site can have multiple ticket
            categories (adult, child, guided tour, etc.) with independent pricing and
            validity windows.
          </p>
          <p className="text-sm text-muted-foreground">
            To add or edit ticket types for a specific site, open the site&apos;s detail page
            from the Heritage catalogue and use the &ldquo;Tickets&rdquo; tab.
          </p>
          <div className="flex gap-3">
            <Button asChild variant="default">
              <Link href="/heritage">Browse Heritage Catalogue</Link>
            </Button>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}
