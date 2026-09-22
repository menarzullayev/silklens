/**
 * Auto-generated API types from OpenAPI schema.
 *
 * To regenerate (requires backend running):
 *   make api-run                  # in repo root — starts FastAPI on :8000
 *   cd apps/admin
 *   pnpm add -D openapi-typescript  # install once if not present
 *   pnpm generate:types
 *
 * The script calls:
 *   openapi-typescript http://localhost:8000/openapi.json \
 *     -o src/types/api.gen.ts --alphabetize
 *
 * Generated: 2026-05-23 (placeholder — run pnpm generate:types for real output)
 * Source: http://localhost:8000/openapi.json
 *
 * Until full auto-generation is bootstrapped, this file contains manually
 * maintained supplementary types that are not yet in src/types/api.ts.
 * Cross-reference: src/types/api.ts for the primary hand-written definitions.
 */

// ---------------------------------------------------------------------------
// Heritage (supplementary fields not in HeritageOut)
// ---------------------------------------------------------------------------

export interface ApiHeritagePage {
  items: ApiHeritage[];
  total: number;
  limit: number;
  offset: number;
}

export interface ApiHeritage {
  id: string;
  pub_id: string;
  kind_slug: string;
  name: Record<string, string>;
  summary_md: Record<string, string>;
  description_md: Record<string, string>;
  tags: string[];
  status: string;
  country_code?: string;
  lat?: number;
  lng?: number;
  confidence_score: number;
  revision: number;
  created_at: string;
  updated_at: string;
}

// ---------------------------------------------------------------------------
// Billing / plans
// ---------------------------------------------------------------------------

export interface ApiPlan {
  slug: string;
  display_name: Record<string, string>;
  description: Record<string, string>;
  sort_order: number;
  is_active: boolean;
}

// ---------------------------------------------------------------------------
// Notifications
// ---------------------------------------------------------------------------

export interface ApiNotification {
  id: string;
  category_slug: string;
  title: string;
  body: string;
  read_at?: string;
  created_at: string;
}

// ---------------------------------------------------------------------------
// Gamification / XP
// ---------------------------------------------------------------------------

export interface ApiXpBalance {
  current_xp: number;
  lifetime_xp: number;
  weekly_xp: number;
  level: number;
  next_level: number;
  xp_to_next_level: number;
  progress_pct: number;
}
