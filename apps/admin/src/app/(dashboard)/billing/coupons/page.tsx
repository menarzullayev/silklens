import type { Metadata } from 'next';
import { Tag } from 'lucide-react';

import { apiFetch } from '@/lib/api/client';
import { PageHeader } from '@/components/layout/page-header';
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import type { CouponOut } from '@/types/api';

export const metadata: Metadata = {
  title: 'Coupons',
};

// SILK-0161: Coupon management page — reads from GET /v1/admin/billing/coupons.
// Displays active discount codes with redemption counts and expiry status.
// Full CRUD management (create / deactivate) lands once the admin coupon API
// endpoint is shipped (currently write path is migration-only).

export default async function CouponsPage(): Promise<JSX.Element> {
  let coupons: CouponOut[] = [];
  try {
    const data = await apiFetch<CouponOut[]>({
      path: '/v1/admin/billing/coupons',
    });
    coupons = Array.isArray(data) ? data : [];
  } catch {
    // Endpoint may not be deployed yet — degrade gracefully.
  }

  return (
    <div className="space-y-6">
      <PageHeader
        title="Coupons"
        subtitle="Discount codes — redemption counts and expiry status"
      />

      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Tag className="h-4 w-4" aria-hidden />
            Active Coupons ({coupons.length})
          </CardTitle>
        </CardHeader>
        <CardContent>
          {coupons.length === 0 ? (
            <div className="space-y-4">
              <p className="text-sm text-muted-foreground">
                No coupons found. The backend coupon list endpoint may not yet be deployed.
                Coupons are currently managed via migration seed data.
              </p>
              <div className="rounded-lg border bg-muted/40 p-4">
                <p className="mb-2 text-xs font-medium uppercase tracking-wide text-muted-foreground">
                  Demo coupon codes (seeded via migration)
                </p>
                <div className="space-y-1.5">
                  {[
                    { code: 'SILKROAD2026', description: '20% off — launch promotion' },
                    { code: 'WELCOME10', description: '10% off — new user onboarding' },
                    { code: 'FLATFIVE', description: '$5 off — flat discount' },
                  ].map(({ code, description }) => (
                    <div key={code} className="flex items-center gap-3">
                      <code className="rounded bg-background px-2 py-0.5 font-mono text-sm font-medium">
                        {code}
                      </code>
                      <span className="text-sm text-muted-foreground">{description}</span>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          ) : (
            <div className="space-y-2">
              {coupons.map((coupon) => (
                <div
                  key={coupon.id}
                  className="flex items-center justify-between rounded-lg border p-3"
                >
                  <div className="flex items-center gap-3">
                    <Tag className="h-4 w-4 shrink-0 text-muted-foreground" aria-hidden />
                    <div>
                      <p className="font-mono font-medium">{coupon.code}</p>
                      <p className="text-sm text-muted-foreground">
                        {coupon.discount_type === 'pct'
                          ? `${coupon.discount_value}% off`
                          : `$${coupon.discount_value} off`}
                        {coupon.max_redemptions
                          ? ` · ${coupon.redemption_count ?? 0}/${coupon.max_redemptions} uses`
                          : coupon.redemption_count
                            ? ` · ${coupon.redemption_count} uses`
                            : ''}
                        {coupon.expires_at
                          ? ` · expires ${new Date(coupon.expires_at).toLocaleDateString()}`
                          : ''}
                      </p>
                    </div>
                  </div>
                  <div className="flex shrink-0 gap-2">
                    <Badge variant={coupon.is_active ? 'default' : 'secondary'}>
                      {coupon.is_active ? 'Active' : 'Inactive'}
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
