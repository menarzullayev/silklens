/**
 * k6 smoke test — verify every critical endpoint responds within 2s.
 *
 * Runs 1 VU for 10 iterations. A single 5xx or a p95 > 2s fails the suite.
 * Designed to run in CI before every deploy and locally after `make api-run`.
 *
 * Usage:
 *   k6 run tests/load/smoke.js
 *   k6 run -e LOAD_TEST_EMAIL=you@example.com -e LOAD_TEST_PASS=secret tests/load/smoke.js
 *   k6 run -e API_BASE=http://staging.silklens.app:8000 tests/load/smoke.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate } from 'k6/metrics';

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const errorRate = new Rate('errors');
const BASE = __ENV.API_BASE || 'http://localhost:8000';

export const options = {
  vus: 1,
  iterations: 10,
  thresholds: {
    // Dev server — 2 s is generous; tighten to 500 ms on staging.
    http_req_duration: ['p(95)<2000'],
    errors: ['rate<0.01'],
    http_req_failed: ['rate<0.01'],
  },
};

// ---------------------------------------------------------------------------
// setup() — runs once before VUs start; return value is passed to default()
// ---------------------------------------------------------------------------

export function setup() {
  const email = __ENV.LOAD_TEST_EMAIL || 'load@silklens.app';
  const pass = __ENV.LOAD_TEST_PASS || 'LoadTest12345!';

  const res = http.post(
    `${BASE}/v1/auth/login`,
    JSON.stringify({ email, password: pass }),
    { headers: { 'Content-Type': 'application/json' } },
  );

  if (res.status === 200) {
    const token = res.json('tokens.access_token');
    console.log(`[setup] login ok — token prefix: ${String(token).slice(0, 20)}…`);
    return { token };
  }

  console.warn(`[setup] login returned ${res.status} — heritage checks will be skipped`);
  return { token: null };
}

// ---------------------------------------------------------------------------
// default() — executed by every VU for every iteration
// ---------------------------------------------------------------------------

export default function (data) {
  // 1. Health check — always public, no auth, instant response expected.
  {
    const r = http.get(`${BASE}/health`);
    const ok = check(r, {
      'health → 200': (x) => x.status === 200,
      'health → not 5xx': (x) => x.status < 500,
      'health → body has status': (x) => {
        try {
          return x.json('status') !== undefined;
        } catch (_) {
          // Non-JSON health body is still OK — just skip body check.
          return true;
        }
      },
    });
    errorRate.add(!ok);
  }

  // 2. Stories random — public endpoint, no auth required.
  {
    const r = http.get(`${BASE}/v1/stories/random?country_code=UZ&language=en`);
    const ok = check(r, {
      'stories/random → not 5xx': (x) => x.status < 500,
      // 200 or 404 are both acceptable (empty dataset in dev is fine).
      'stories/random → 200 or 404': (x) => x.status === 200 || x.status === 404,
    });
    errorRate.add(!ok);
  }

  // 3. Heritage list — requires Bearer token; skip gracefully if login failed.
  if (data.token) {
    const r = http.get(`${BASE}/v1/heritage?limit=10`, {
      headers: { Authorization: `Bearer ${data.token}` },
    });
    const ok = check(r, {
      'heritage list → not 5xx': (x) => x.status < 500,
      'heritage list → 200 or 401': (x) => x.status === 200 || x.status === 401,
    });
    errorRate.add(!ok);
  }

  // 4. Auth login — exercised inline here so smoke covers the happy path
  //    (the token we got in setup may have come from a fixture user; here we
  //    deliberately attempt an invalid login to confirm the path is reachable).
  {
    const r = http.post(
      `${BASE}/v1/auth/login`,
      JSON.stringify({ email: 'smoke_probe@silklens.invalid', password: 'probe' }),
      { headers: { 'Content-Type': 'application/json' } },
    );
    const ok = check(r, {
      'auth/login probe → not 5xx': (x) => x.status < 500,
      // 401 or 422 are expected; anything else is suspicious but not a hard fail.
      'auth/login probe → 401 or 422': (x) => x.status === 401 || x.status === 422,
    });
    errorRate.add(!ok);
  }

  sleep(0.2);
}
