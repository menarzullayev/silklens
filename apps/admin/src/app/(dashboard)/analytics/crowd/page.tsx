import type { Metadata } from 'next';
import { Construction } from 'lucide-react';

import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent } from '@/components/ui/card';

export const metadata: Metadata = {
  title: 'Crowd Analytics',
};

// SILK-0164: Crowd density analytics — backend endpoint not yet exposed.
// Schema landed in migration `20260514_0088_crowd_signals.py`. Once the
// `/v1/admin/analytics/crowd` time-series aggregator ships, replace the
// placeholder with site-level density heatmaps and peak-hour rollups.

export default function CrowdAnalyticsPage(): JSX.Element {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Crowd Analytics"
        subtitle="Heritage site density signals, peak hours and bottleneck detection"
      />
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
          <Construction className="mb-4 h-12 w-12 text-muted-foreground" aria-hidden />
          <h3 className="text-lg font-semibold">Under Development</h3>
          <p className="mt-2 max-w-md text-sm text-muted-foreground">
            Backend endpoints for crowd analytics are not yet exposed via the admin API.
            Schema is in migration{' '}
            <code className="font-mono text-xs">20260514_0088_crowd_signals.py</code>.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
