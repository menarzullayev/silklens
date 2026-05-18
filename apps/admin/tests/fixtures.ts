import type { Page } from '@playwright/test';

/**
 * Mock fixtures + helpers for Playwright. The admin panel proxies every fetch
 * through `apiFetch`, so intercepting `http://localhost:8000/v1/**` is enough.
 *
 * Note: the API base URL is the one set in `.env.example` (which is what the
 * dev server picks up when no `.env.local` is present).
 */

export const API_BASE = 'http://localhost:8000';

export const FAKE_LOGIN_RESPONSE = {
  user: {
    id: '01HXXXXXXXXXXXXXXXXXXXXXXX',
    pub_id: 'usr_demo',
    tenant_id: '00000000-0000-0000-0000-000000000001',
    residency_region: 'uz' as const,
    trust_tier: 'super_admin',
    preferred_locale: 'uz',
    preferred_timezone: 'UTC',
    is_verified: true,
  },
  tokens: {
    access_token: 'fake-access-token',
    refresh_token: 'fake-refresh-token',
    token_type: 'Bearer' as const,
    expires_in: 3600,
  },
};

export const FAKE_HERITAGE_PAGE = {
  items: [
    {
      id: '01HHERITAGE0000000000000001',
      pub_id: 'her_registan',
      kind_slug: 'monument',
      name: { en: 'Registan', uz: 'Registon' },
      summary_md: { en: 'Heart of Samarkand.' },
      description_md: {},
      tags: ['silk-road', 'unesco'],
      status: 'published',
      country_code: 'UZ',
      admin_path: 'uz.samarkand',
      latitude: 39.6547,
      longitude: 66.9758,
      period_start_year: 1417,
      period_end_year: 1660,
      unesco_inscription_year: 2001,
      hero_media_id: null,
      confidence_score: 92,
      revision: 3,
    },
    {
      id: '01HHERITAGE0000000000000002',
      pub_id: 'her_itchan_kala',
      kind_slug: 'historic_quarter',
      name: { en: 'Itchan Kala', uz: 'Ichon-Qal’a' },
      summary_md: {},
      description_md: {},
      tags: ['silk-road'],
      status: 'review',
      country_code: 'UZ',
      admin_path: 'uz.khorezm',
      latitude: 41.3781,
      longitude: 60.3617,
      period_start_year: 1700,
      period_end_year: 1900,
      unesco_inscription_year: 1990,
      hero_media_id: null,
      confidence_score: 85,
      revision: 1,
    },
  ],
  total: 2,
  limit: 20,
  offset: 0,
};

export const FAKE_TENANTS_PAGE = {
  items: [
    {
      id: '00000000-0000-0000-0000-000000000001',
      slug: 'silklens',
      display_name: { en: 'SilkLens', uz: 'SilkLens' },
      status: 'active',
      plan_tier: 'enterprise',
      created_at: '2025-01-01T00:00:00Z',
      updated_at: '2025-05-18T12:00:00Z',
    },
    {
      id: '00000000-0000-0000-0000-000000000002',
      slug: 'acme',
      display_name: { en: 'Acme Heritage' },
      status: 'active',
      plan_tier: 'free',
      created_at: '2025-04-01T00:00:00Z',
      updated_at: '2025-05-10T00:00:00Z',
    },
  ],
  total: 2,
  limit: 20,
  offset: 0,
};

export const FAKE_BRANDING = {
  app_name: { en: 'SilkLens', uz: 'SilkLens' },
  logo_url: 'https://cdn.silklens.app/logos/light.svg',
  logo_dark_url: null,
  primary_color: '#1e3a8a',
  accent_color: '#f59e0b',
  splash_url: null,
  font_family: 'Inter',
  theme_mode_default: 'system',
  extra: {},
};

export const FAKE_VOCAB_KINDS = {
  slug: 'heritage_kinds',
  is_hierarchical: false,
  items: [
    {
      slug: 'monument',
      display_name: { en: 'Monument', uz: 'Yodgorlik' },
      description: {},
      parent_slug: null,
      sort_order: 1,
    },
    {
      slug: 'historic_quarter',
      display_name: { en: 'Historic quarter' },
      description: {},
      parent_slug: null,
      sort_order: 2,
    },
  ],
};

export const FAKE_VOCAB_REGIONS = {
  slug: 'residency_regions',
  is_hierarchical: false,
  items: [
    {
      slug: 'uz',
      display_name: { en: 'Uzbekistan' },
      description: {},
      parent_slug: null,
      sort_order: 1,
    },
    {
      slug: 'eu',
      display_name: { en: 'European Union' },
      description: {},
      parent_slug: null,
      sort_order: 2,
    },
  ],
};

export const FAKE_AI_MODELS = [
  {
    slug: 'gpt-4o',
    name: { en: 'GPT-4o' },
    task_type: 'llm',
    provider_slug: 'openai',
    is_enabled: true,
    sort_order: 10,
  },
  {
    slug: 'claude-sonnet',
    name: { en: 'Claude Sonnet' },
    task_type: 'llm',
    provider_slug: 'anthropic',
    is_enabled: false,
    sort_order: 20,
  },
];

export const FAKE_AI_CHAINS = [
  {
    slug: 'llm-default',
    task_type: 'llm',
    name: { en: 'Default LLM chain' },
    is_active: true,
    steps: [
      { step_order: 1, model_slug: 'gpt-4o', max_latency_ms: 5000, conditions: {} },
      { step_order: 2, model_slug: 'claude-sonnet', max_latency_ms: 8000, conditions: {} },
    ],
  },
];

export const FAKE_FEATURE_FLAGS = [
  {
    key: 'ai.live_translation',
    enabled: true,
    rollout_kind: 'boolean',
    rollout_value: {},
    description: 'Stream translations as user types',
  },
];

export const FAKE_SYSTEM_SETTINGS = [
  {
    key: 'ai.default_model',
    value: 'gpt-4o',
    value_type: 'string',
    scope: 'tenant',
    description: 'Primary LLM',
    is_secret: false,
  },
  {
    key: 'moderation.auto_flag_threshold',
    value: 75,
    value_type: 'int',
    scope: 'tenant',
    description: 'Auto-flag UGC above this score',
    is_secret: false,
  },
];

/**
 * Install a uniform mock for every backend endpoint the admin reaches.
 */
export async function mockBackend(page: Page): Promise<void> {
  await page.route(`${API_BASE}/v1/**`, async (route) => {
    const url = new URL(route.request().url());
    const method = route.request().method();
    const path = url.pathname;

    if (path === '/v1/auth/login' && method === 'POST') {
      return route.fulfill({ json: FAKE_LOGIN_RESPONSE });
    }
    if (path === '/v1/auth/refresh' && method === 'POST') {
      return route.fulfill({ json: FAKE_LOGIN_RESPONSE });
    }
    if (path === '/v1/auth/me') {
      return route.fulfill({
        json: {
          user: FAKE_LOGIN_RESPONSE.user,
          session_id: '00000000-0000-0000-0000-000000000099',
          trust_tier: FAKE_LOGIN_RESPONSE.user.trust_tier,
        },
      });
    }
    if (path === '/v1/heritage' && method === 'GET') {
      return route.fulfill({ json: FAKE_HERITAGE_PAGE });
    }
    if (path.startsWith('/v1/heritage/') && path.endsWith('/reviews')) {
      return route.fulfill({ json: { items: [], total: 0, limit: 5, offset: 0 } });
    }
    if (path.startsWith('/v1/heritage/') && path.endsWith('/revisions')) {
      return route.fulfill({ json: { items: [], total: 0, limit: 20, offset: 0 } });
    }
    if (path.startsWith('/v1/heritage/') && method === 'GET') {
      return route.fulfill({ json: FAKE_HERITAGE_PAGE.items[0] });
    }
    if (path === '/v1/admin/tenants' && method === 'GET') {
      return route.fulfill({ json: FAKE_TENANTS_PAGE });
    }
    if (path === '/v1/admin/tenants' && method === 'POST') {
      const body = JSON.parse(route.request().postData() ?? '{}');
      return route.fulfill({
        status: 201,
        json: {
          id: '00000000-0000-0000-0000-000000000099',
          slug: body.slug,
          display_name: body.display_name,
          status: 'active',
          plan_tier: 'free',
          created_at: new Date().toISOString(),
          updated_at: new Date().toISOString(),
        },
      });
    }
    if (path.startsWith('/v1/admin/tenants/') && path.endsWith('/branding') && method === 'GET') {
      return route.fulfill({ json: FAKE_BRANDING });
    }
    if (path.startsWith('/v1/admin/tenants/') && path.endsWith('/branding') && method === 'PUT') {
      const body = JSON.parse(route.request().postData() ?? '{}');
      return route.fulfill({
        json: { ...FAKE_BRANDING, ...body },
      });
    }
    if (path === '/v1/admin/system-settings' && method === 'GET') {
      return route.fulfill({ json: FAKE_SYSTEM_SETTINGS });
    }
    if (path === '/v1/admin/feature-flags' && method === 'GET') {
      return route.fulfill({ json: FAKE_FEATURE_FLAGS });
    }
    if (path === '/v1/ai/models' && method === 'GET') {
      return route.fulfill({ json: FAKE_AI_MODELS });
    }
    if (path === '/v1/ai/fallback-chains' && method === 'GET') {
      return route.fulfill({ json: FAKE_AI_CHAINS });
    }
    if (path.startsWith('/v1/vocab/heritage_kinds')) {
      return route.fulfill({ json: FAKE_VOCAB_KINDS });
    }
    if (path.startsWith('/v1/vocab/residency_regions')) {
      return route.fulfill({ json: FAKE_VOCAB_REGIONS });
    }
    return route.fulfill({ status: 404, json: { detail: 'mock not implemented' } });
  });
}

export async function signInAsAdmin(page: Page): Promise<void> {
  await mockBackend(page);
  await page.goto('/login');
  await page.locator('input[type="email"]').fill('admin@silklens.app');
  await page.locator('input[type="password"]').fill('DemoPassword12345');
  await page.locator('button[type="submit"]').first().click();
  await page.waitForURL((url) => !url.pathname.startsWith('/login'));
}
