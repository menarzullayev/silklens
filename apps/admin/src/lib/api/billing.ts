import { apiFetch } from './client';

// --- Billing plans -----------------------------------------------------------

export interface I18nString {
  readonly en?: string;
  readonly uz?: string;
  readonly ru?: string;
  readonly [lang: string]: string | undefined;
}

export interface BillingPlan {
  readonly slug: string;
  readonly display_name: I18nString | string;
  readonly description?: I18nString | string;
  readonly is_active?: boolean;
  readonly features?: readonly string[];
  readonly pricing_zones?: Record<string, unknown>;
}

export interface BillingPlansPage {
  readonly items?: readonly BillingPlan[];
  readonly total?: number;
  readonly [key: string]: unknown;
}

export function getPlans(pricingZone?: string): Promise<BillingPlansPage> {
  return apiFetch<BillingPlansPage>({
    path: '/v1/billing/plans',
    query: pricingZone ? { pricing_zone: pricingZone } : undefined,
  });
}

// --- Reseller applications ---------------------------------------------------

export interface ResellerApplication {
  readonly id: string;
  readonly pub_id?: string;
  readonly company_name: string;
  readonly contact_email: string;
  readonly status: 'pending' | 'approved' | 'rejected';
  readonly created_at: string;
  readonly [key: string]: unknown;
}

export interface ResellerApplicationsPage {
  readonly items?: readonly ResellerApplication[];
  readonly total?: number;
  readonly [key: string]: unknown;
}

export function getResellerApplications(params?: {
  status?: string;
  limit?: number;
  offset?: number;
}): Promise<ResellerApplicationsPage> {
  return apiFetch<ResellerApplicationsPage>({
    path: '/v1/admin/reseller/applications',
    query: {
      status: params?.status,
      limit: params?.limit ?? 20,
      offset: params?.offset ?? 0,
    },
  });
}
