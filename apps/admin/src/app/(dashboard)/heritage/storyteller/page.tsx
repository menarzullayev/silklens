import type { Metadata } from 'next';
import { Construction } from 'lucide-react';

import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent } from '@/components/ui/card';

export const metadata: Metadata = {
  title: 'Storyteller',
};

// SILK-0165: Heritage storyteller management — backend endpoint not yet exposed.
// Schema landed in migration `20260512_0082_storyteller.py` (story arcs,
// narration scripts, scene timing). Once the admin storyteller router ships,
// replace the placeholder with the story editor and voice-actor assignment UI.

export default function HeritageStorytellerPage(): JSX.Element {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Heritage Storyteller"
        subtitle="Curated narrative arcs and voice-acted scripts for heritage sites"
      />
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
          <Construction className="mb-4 h-12 w-12 text-muted-foreground" aria-hidden />
          <h3 className="text-lg font-semibold">Under Development</h3>
          <p className="mt-2 max-w-md text-sm text-muted-foreground">
            Backend endpoints for storyteller management are not yet exposed via the admin
            API. Schema is in migration{' '}
            <code className="font-mono text-xs">20260512_0082_storyteller.py</code>.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
