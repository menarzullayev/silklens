import type { Metadata } from 'next';
import { Construction } from 'lucide-react';

import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent } from '@/components/ui/card';

export const metadata: Metadata = {
  title: 'Trip Analytics',
};

// SILK-0162: Trip analytics page — backend endpoint not yet exposed.
// Schema landed in migration `20260513_0085_trip_planner.py`. Once the
// `/v1/admin/analytics/trips` aggregator router ships, replace the
// placeholder with route, funnel and conversion charts.

export default function TripsAnalyticsPage(): JSX.Element {
  return (
    <div className="space-y-6">
      <PageHeader
        title="Trip Analytics"
        subtitle="Itinerary planning, completion and conversion metrics"
      />
      <Card>
        <CardContent className="flex flex-col items-center justify-center py-16 text-center">
          <Construction className="mb-4 h-12 w-12 text-muted-foreground" aria-hidden />
          <h3 className="text-lg font-semibold">Under Development</h3>
          <p className="mt-2 max-w-md text-sm text-muted-foreground">
            Backend endpoints for trip analytics are not yet exposed via the admin API.
            Schema is in migration{' '}
            <code className="font-mono text-xs">20260513_0085_trip_planner.py</code>.
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
