/**
 * k6 auth-path stress test — hammers POST /v1/auth/login to measure throughput
 * and latency of the full authentication pipeline (Argon2id hash, DB lookup,
 * JWT issuance path) under sustained concurrency.
 *
 * Each iteration uses a unique email derived from VU + iteration counters so
 * requests are distinct to the DB (avoids query-cache skew). The vast majority
 * will return 401 (user not found) — that is expected and intentional. We only
 * care that the server does NOT return 5xx and that p95 latency stays sane.
 *
 * Why Argon2id hurts here:
 *   Even a "user not found" path does a timing-safe password hash to prevent
 *   user-enumeration. 5 VUs hammering this reveals CPU saturation quickly.
 *
 * Usage:
 *   k6 run tests/load/auth-stress.js
 *   k6 run -e API_BASE=http://staging.silklens.app:8000 tests/load/auth-stress.js
 */

import http from 'k6/http';
import { check, sleep } from 'k6';
import { Rate, Counter } from 'k6/metrics';

// ---------------------------------------------------------------------------
// Config
// ---------------------------------------------------------------------------

const BASE = __ENV.API_BASE || 'http://localhost:8000';

/**
 * Custom metrics.
 * server_errors: 5xx responses — should stay near 0.
 * auth_401s:     expected "user not found" responses — informational only.
 */
const serverErrors = new Rate('server_errors');
const auth401s = new Counter('auth_401s');
const auth200s = new Counter('auth_200s');

export const options = {
  scenarios: {
    auth_hammer: {
      executor: 'constant-vus',
      vus: 5,
      duration: '30s',
      gracefulStop: '5s',
    },
  },

  thresholds: {
    // Auth hashes are expensive — 3 s is the outer bound on a loaded dev box.
    http_req_duration: ['p(95)<3000', 'p(99)<5000'],

    // Most requests will be 401s, which k6 counts as "failed" by default.
    // We override with a very permissive threshold — the real signal is
    // server_errors (5xx), which must stay near zero.
    http_req_failed: ['rate<0.95'],

    // This is the threshold that actually matters:
    server_errors: ['rate<0.01'],
  },
};

// ---------------------------------------------------------------------------
// default() — no setup() needed; all requests are intentionally invalid users
// ---------------------------------------------------------------------------

export default function () {
  // Generate a unique email per VU+iteration. Using VU and ITER globals
  // guarantees no two concurrent iterations share the same email, which
  // would trigger the "user not found" fast-path cache at the repo layer.
  const email = `load_vu${__VU}_iter${__ITER}@silklens.app`;
  const password = 'WrongPassword!99';

  const res = http.post(
    `${BASE}/v1/auth/login`,
    JSON.stringify({ email, password }),
    {
      headers: { 'Content-Type': 'application/json' },
      // Tag requests so Grafana can split by outcome.
      tags: { name: 'auth_login_stress' },
    },
  );

  // Track 5xx — these indicate a real problem.
  const is5xx = res.status >= 500;
  serverErrors.add(is5xx);

  // Tally outcomes for informational metrics.
  if (res.status === 401) auth401s.add(1);
  if (res.status === 200) auth200s.add(1);

  // The core contract: server must not return 5xx regardless of credentials.
  check(res, {
    'auth → not 5xx': (r) => r.status < 500,
    // 401 = user not found (expected), 422 = validation error (also fine).
    'auth → 401 or 422 (expected)': (r) => r.status === 401 || r.status === 422,
  });

  // Short think-time — this is a stress test, not a spike test.
  // Remove the sleep() entirely to simulate a true spike scenario.
  sleep(0.1);
}
