/**
 * Hand-written types for the SilkLens FastAPI backend.
 *
 * Mirrors the Pydantic response models in `services/api/src/api/routers/*`.
 * Until OpenAPI regen is wired (see README), these are the contract.
 *
 *   pnpm dlx openapi-typescript http://localhost:8000/openapi.json \
 *     -o src/types/api.ts
 */

// --- Auth ------------------------------------------------------------------

export type ResidencyRegion = 'uz' | 'eu' | 'us' | 'global';

export interface AuthUser {
  id: string;
  pub_id: string;
  tenant_id: string;
  residency_region: ResidencyRegion;
  trust_tier: string;
  preferred_locale: string;
  preferred_timezone: string;
  is_verified: boolean;
}

export interface TokenBundle {
  access_token: string;
  refresh_token: string;
  token_type: 'Bearer';
  expires_in: number;
}

export interface LoginResponse {
  user: AuthUser;
  tokens: TokenBundle;
}

export interface MeResponse {
  user: AuthUser;
  session_id: string;
  trust_tier: string;
}

// --- Heritage --------------------------------------------------------------

export type HeritageStatus =
  | 'draft'
  | 'review'
  | 'published'
  | 'archived'
  | 'rejected';

export interface HeritageOut {
  id: string;
  pub_id: string;
  kind_slug: string;
  name: Record<string, string>;
  summary_md: Record<string, string>;
  description_md: Record<string, string>;
  tags: readonly string[];
  status: HeritageStatus;
  country_code: string | null;
  admin_path: string | null;
  latitude: string | number | null;
  longitude: string | number | null;
  period_start_year: number | null;
  period_end_year: number | null;
  unesco_inscription_year: number | null;
  hero_media_id: string | null;
  confidence_score: number;
  revision: number;
}

export interface HeritagePage {
  items: readonly HeritageOut[];
  total: number;
  limit: number;
  offset: number;
}

export interface HeritageCreate {
  kind_slug: string;
  name: Record<string, string>;
  summary_md?: Record<string, string>;
  description_md?: Record<string, string>;
  tags?: readonly string[];
  country_code?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  period_start_year?: number | null;
  period_end_year?: number | null;
  unesco_inscription_year?: number | null;
  status?: HeritageStatus;
}

export interface HeritagePatch {
  name?: Record<string, string>;
  summary_md?: Record<string, string>;
  description_md?: Record<string, string>;
  tags?: readonly string[];
  country_code?: string | null;
  latitude?: number | null;
  longitude?: number | null;
  period_start_year?: number | null;
  period_end_year?: number | null;
  unesco_inscription_year?: number | null;
  hero_media_id?: string | null;
  status?: HeritageStatus;
}

export interface HeritageAlias {
  id: string;
  heritage_id: string;
  alias: string;
  language_tag: string;
  kind: string;
  confidence: number;
  script: string | null;
  source: string | null;
  created_at: string | null;
}

export interface HeritageRevision {
  id: string;
  revision: number;
  action: string;
  actor_user_id: string | null;
  comment: string | null;
  valid_from: string;
  before: Record<string, unknown> | null;
  after: Record<string, unknown>;
}

export interface HeritageRevisionPage {
  items: readonly HeritageRevision[];
  total: number;
  limit: number;
  offset: number;
}

export type HeritageTransition =
  | 'submit'
  | 'approve'
  | 'reject'
  | 'archive'
  | 'restore';

// --- Tenants ---------------------------------------------------------------

export type TenantStatus = 'active' | 'suspended' | 'archived';

export interface TenantOut {
  id: string;
  slug: string;
  display_name: Record<string, string>;
  status: TenantStatus;
  plan_tier: string;
  created_at: string;
  updated_at: string;
}

export interface TenantsPage {
  items: readonly TenantOut[];
  total: number;
  limit: number;
  offset: number;
}

export interface TenantCreateInput {
  slug: string;
  display_name: Record<string, string>;
}

export interface TenantPatchInput {
  display_name?: Record<string, string>;
  status?: TenantStatus;
  plan_tier?: string;
}

// --- Branding --------------------------------------------------------------

export interface BrandingOut {
  app_name: Record<string, string>;
  logo_url: string | null;
  logo_dark_url: string | null;
  primary_color: string | null;
  accent_color: string | null;
  splash_url: string | null;
  font_family: string | null;
  theme_mode_default: string | null;
  extra: Record<string, unknown>;
}

export interface BrandingPutInput {
  app_name?: Record<string, string>;
  logo_url?: string | null;
  logo_dark_url?: string | null;
  primary_color?: string | null;
  accent_color?: string | null;
  splash_url?: string | null;
  font_family?: string | null;
  theme_mode_default?: 'light' | 'dark' | 'system' | 'national' | 'high_contrast';
  extra?: Record<string, unknown>;
}

// --- System settings -------------------------------------------------------

export type SettingValueType =
  | 'string'
  | 'int'
  | 'float'
  | 'bool'
  | 'json'
  | 'duration'
  | 'color'
  | 'url';

export interface SystemSettingOut {
  key: string;
  value: unknown;
  value_type: SettingValueType;
  scope: 'tenant' | 'global' | 'user_overrideable';
  description: string | null;
  is_secret: boolean;
}

export interface SystemSettingPutInput {
  key: string;
  value: unknown;
  value_type: SettingValueType;
  scope?: 'tenant' | 'global' | 'user_overrideable';
  description?: string | null;
  is_secret?: boolean;
}

// --- Feature flags ---------------------------------------------------------

export type RolloutKind =
  | 'boolean'
  | 'percentage'
  | 'user_allowlist'
  | 'user_denylist'
  | 'jsonl_rules';

export interface FeatureFlagOut {
  key: string;
  enabled: boolean;
  rollout_kind: RolloutKind;
  rollout_value: Record<string, unknown>;
  description: string | null;
}

export interface FeatureFlagPutInput {
  enabled: boolean;
  rollout_kind: RolloutKind;
  rollout_value: Record<string, unknown>;
  description?: string | null;
}

// --- AI --------------------------------------------------------------------

export interface AiModelOut {
  slug: string;
  name: Record<string, string>;
  task_type: string;
  provider_slug: string;
  is_enabled: boolean;
  sort_order: number;
}

export interface AiModelPatchInput {
  is_enabled?: boolean;
  sort_order?: number;
}

export interface AiChainStep {
  step_order: number;
  model_slug: string;
  max_latency_ms: number | null;
  conditions: Record<string, unknown>;
}

export interface AiChainOut {
  slug: string;
  task_type: string;
  name: Record<string, string>;
  is_active: boolean;
  steps: readonly AiChainStep[];
}

// --- Vocab -----------------------------------------------------------------

export interface VocabTerm {
  slug: string;
  display_name: Record<string, string>;
  description: Record<string, string>;
  parent_slug: string | null;
  sort_order: number;
}

export interface VocabOut {
  slug: string;
  is_hierarchical: boolean;
  items: readonly VocabTerm[];
}

// --- Reviews ---------------------------------------------------------------

export interface ReviewOut {
  id: string;
  heritage_pub_id: string;
  user_id: string;
  rating: number;
  body: string | null;
  helpful_count: number;
  status: 'visible' | 'hidden' | 'reported' | 'removed';
  created_at: string;
}

export interface ReviewPage {
  items: readonly ReviewOut[];
  total: number;
  limit: number;
  offset: number;
}

// --- Generic ---------------------------------------------------------------

export interface ErrorDetail {
  code: string;
  message: string;
  [k: string]: unknown;
}
