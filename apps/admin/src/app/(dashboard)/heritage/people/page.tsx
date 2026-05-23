import type { Metadata } from 'next';
import { Construction } from 'lucide-react';

import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent } from '@/components/ui/card';

export const metadata: Metadata = {
  title: 'Heritage People & Materials',
};

// SILK-0150: Heritage people + materials catalogue — backend endpoint not yet
// exposed. Schema landed in migration `20260510_0078_heritage_actors.py` and
// covers historical figures, architects, dynasties, and the material taxonomy
// (stone types, ceramic glazes, textile fibres) referenced from heritage_facts.

export default function HeritagePeoplePage(): JSX.Element {
  return (
    <div className="space-y-6">
      <PageHeader
        title="People & Materials"
        subtitle="Historical figures, dynasties, architects and material taxonomy"
      />
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
          <Construction className="mb-4 h-12 w-12 text-muted-foreground" aria-hidden />
          <h3 className="text-lg font-semibold">Under Development</h3>
          <p className="mt-2 max-w-md text-sm text-muted-foreground">
            Backend endpoints for heritage people and materials are not yet exposed via the
            admin API. Schema is in migration{' '}
            <code className="font-mono text-xs">20260510_0078_heritage_actors.py</code>.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
