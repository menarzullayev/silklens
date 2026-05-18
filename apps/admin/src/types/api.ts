/**
 * Placeholder OpenAPI types for the SilkLens FastAPI backend.
 *
 * TODO(ops): Regenerate from `/openapi.json` via `openapi-typescript` once the
 * Identity / Heritage / Monetization routers are live:
 *
 *   pnpm dlx openapi-typescript http://localhost:8000/openapi.json \
 *     -o src/types/api.ts
 *
 * Until then the types below are hand-written *minimum* shapes that are
 * stable enough for the admin to compile against. Anything beyond these
 * shapes must go through `unknown` and a Zod validator at the call site.
 */

export interface TenantSummary {
  id: string;
  slug: string;
  legal_name: string;
  status: 'active' | 'suspended' | 'archived' | 'provisioning';
  default_locale: string;
  default_currency: string;
  is_root: boolean;
}

export interface UserSummary {
  id: string;
  email: string;
  display_name: string | null;
  status: 'active' | 'pending' | 'suspended' | 'deleted';
  residency_region: string;
  created_at: string;
  roles: readonly string[];
}

export interface HeritageSummary {
  id: string;
  tenant_id: string;
  slug: string;
  title: string;
  region: string;
  city: string | null;
  publication_status: 'draft' | 'review' | 'published' | 'archived';
  updated_at: string;
}

export interface ModerationQueueItem {
  id: string;
  tenant_id: string;
  subject_type: 'review' | 'photo' | 'comment' | 'report';
  subject_id: string;
  reason_code: string;
  ai_score: number | null;
  status: 'pending' | 'approved' | 'rejected' | 'escalated';
  created_at: string;
}

export interface AiModelConfig {
  id: string;
  domain: 'vision' | 'tts' | 'translation' | 'llm' | 'embedding';
  provider: string;
  model_key: string;
  is_active: boolean;
  fallback_order: number;
  parameters: Record<string, unknown>;
}

export interface MonetizationProduct {
  id: string;
  tenant_id: string;
  key: string;
  type: 'subscription' | 'one_time' | 'metered' | 'b2b' | 'enterprise' | 'marketplace' | 'tip';
  is_active: boolean;
}

export interface TenantBranding {
  tenant_id: string;
  locale: string;
  app_name: string;
  logo_light_url: string | null;
  logo_dark_url: string | null;
  splash_url: string | null;
  primary_color: string | null;
  secondary_color: string | null;
  font_family: string | null;
}

export interface AnalyticsOverview {
  active_users_24h: number;
  active_users_7d: number;
  heritage_views_24h: number;
  premium_subscribers: number;
  revenue_mtd_usd: number;
}

export interface Paginated<T> {
  items: readonly T[];
  total: number;
  page: number;
  page_size: number;
}
