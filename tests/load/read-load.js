/**
 * k6 read-heavy load test — simulates the most common SilkLens production
 * traffic pattern: users browsing stories and heritage items.
 *
 * Traffic mix (per iteration):
 *   70 % → GET /v1/stories/random?country_code=UZ&language=en  (public)
 *   30 % → GET /v1/heritage?limit=10                           (authenticated)
 *
 * Ramp shape:
 *   0 → 20 VUs over 30 s  →  hold 60 s  →  0 VUs over 15 s
 *
 * Usage:
 *   k6 run tests/load/read-load.js
 *   k6 run -e API_BASE=http://staging.silklens.app:8000 \
 *          -e LOAD_TEST_EMAIL=bench@silklens.app \
 *          -e LOAD_TEST_PASS=Bench12345! \
 *          tests/load/read-load.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Trend } from 'k6/metrics';

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const BASE = __ENV.API_BASE || 'http://localhost:8000';

/** Custom metrics — appear as separate series in k6 Cloud / Grafana. */
const errorRate = new Rate('errors');
const storyDuration = new Trend('story_req_duration', true);
const heritageDuration = new Trend('heritage_req_duration', true);

export const options = {
  scenarios: {
    /**
     * ramp_up: smoothly increase load from 0 → 20 VUs.
     * hold:    sustain peak load for 60 s.
     * ramp_down: graceful wind-down — avoids thundering-herd on shutdown.
     */
    read_traffic: {
      executor: 'ramping-vus',
      startVUs: 0,
      stages: [
        { duration: '30s', target: 20 },  // ramp up
        { duration: '60s', target: 20 },  // hold at peak
        { duration: '15s', target: 0  },  // ramp down
      ],
      gracefulRampDown: '10s',
    },
  },

  thresholds: {
    // Dev server SLA — tighten to p(95)<500 on staging.
    http_req_duration:  ['p(95)<1000', 'p(99)<2000'],
    story_req_duration: ['p(95)<1000'],
    heritage_req_duration: ['p(95)<1200'],
    errors:             ['rate<0.02'],
    http_req_failed:    ['rate<0.02'],
  },
};

// ---------------------------------------------------------------------------
// setup() — single login before VUs start; token shared read-only across all
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
    console.log(`[setup] authenticated — token prefix: ${String(token).slice(0, 20)}…`);
    return { token };
  }

  console.warn(
    `[setup] login failed (${res.status}) — heritage requests will be skipped. ` +
    'Set LOAD_TEST_EMAIL / LOAD_TEST_PASS to a valid test user.',
  );
  return { token: null };
}

// ---------------------------------------------------------------------------
// default() — VU iteration function
// ---------------------------------------------------------------------------

export default function (data) {
  const roll = Math.random();

  if (roll < 0.70) {
    // -----------------------------------------------------------------------
    // 70 % — Public stories browse (no auth)
    // -----------------------------------------------------------------------
    const start = Date.now();
    const r = http.get(`${BASE}/v1/stories/random?country_code=UZ&language=en`);
    storyDuration.add(Date.now() - start);

    const ok = check(r, {
      'stories/random → not 5xx': (x) => x.status < 500,
      'stories/random → 200 or 404': (x) => x.status === 200 || x.status === 404,
    });
    errorRate.add(!ok);

  } else {
    // -----------------------------------------------------------------------
    // 30 % — Authenticated heritage list browse
    // -----------------------------------------------------------------------
    if (!data.token) {
      // No token available — fall back to a public health ping so the VU
      // isn't idle (keeps the load shape honest).
      http.get(`${BASE}/health`);
      return;
    }

    const start = Date.now();
    const r = http.get(`${BASE}/v1/heritage?limit=10`, {
      headers: { Authorization: `Bearer ${data.token}` },
    });
    heritageDuration.add(Date.now() - start);

    const ok = check(r, {
      'heritage list → not 5xx': (x) => x.status < 500,
      'heritage list → 200': (x) => x.status === 200,
    });
    errorRate.add(!ok);
  }

  // Realistic think-time: 0.5 – 1.5 s between page loads.
  sleep(0.5 + Math.random());
}
