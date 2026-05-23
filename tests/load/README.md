# SilkLens — k6 Load Tests

Performance and reliability tests for the FastAPI backend at `http://localhost:8000`.
These scripts use [k6](https://k6.io) — a modern, developer-friendly load-testing tool
written in Go with a JavaScript scripting layer.

---

## Prerequisites

### Install k6

**macOS (Homebrew)**
```bash
brew install k6
```

**Ubuntu / Debian (apt)**
```bash
sudo gpg -k
sudo gpg --no-default-keyring \
  --keyring /usr/share/keyrings/k6-archive-keyring.gpg \
  --keyserver hkp://keyserver.ubuntu.com:80 \
  --recv-keys C5AD17C747E3415A3642D57D77C6C491D6AC1D69
echo "deb [signed-by=/usr/share/keyrings/k6-archive-keyring.gpg] https://dl.k6.io/deb stable main" \
  | sudo tee /etc/apt/sources.list.d/k6.list
sudo apt-get update
sudo apt-get install k6
```

**Docker (no install required)**
```bash
docker run --rm -it \
  --network host \
  grafana/k6 run - < tests/load/smoke.js
```

Verify: `k6 version` should print `k6 v0.5x.x`.

---

## Available scripts

| Script | Purpose | VUs | Duration | Auth needed |
|---|---|---|---|---|
| `smoke.js` | Verify all critical endpoints respond — run after every deploy | 1 | ~10 iterations | Optional (skips heritage if no token) |
| `read-load.js` | Sustained read traffic — ramp 0→20 VUs, hold, ramp down | up to 20 | ~105 s | Optional (skips heritage if no token) |
| `auth-stress.js` | Hammer the auth pipeline — measure Argon2id throughput | 5 | 30 s | None (all requests fail auth intentionally) |

---

## Running the tests

### Makefile target (recommended)

```bash
# Smoke — quick sanity check after starting the API
make load-smoke

# Read load — full ramp/hold/ramp scenario
make load-read

# Auth stress — Argon2id throughput test
make load-auth

# Run all three sequentially
make load-test
```

### Run directly with k6

```bash
# Smoke test
k6 run tests/load/smoke.js

# Read-heavy load test
k6 run tests/load/read-load.js

# Auth stress test
k6 run tests/load/auth-stress.js
```

### Docker alternative (no local k6 install)

```bash
# Smoke
docker run --rm -it --network host \
  -v "$(pwd)/tests/load:/scripts" \
  grafana/k6 run /scripts/smoke.js

# With env vars
docker run --rm -it --network host \
  -v "$(pwd)/tests/load:/scripts" \
  -e LOAD_TEST_EMAIL=you@example.com \
  -e LOAD_TEST_PASS=YourPassword! \
  grafana/k6 run /scripts/read-load.js
```

---

## Environment variables

| Variable | Default | Description |
|---|---|---|
| `API_BASE` | `http://localhost:8000` | Base URL of the API under test. Override for staging or CI. |
| `LOAD_TEST_EMAIL` | `load@silklens.app` | Email of a pre-seeded test user for authenticated endpoints. |
| `LOAD_TEST_PASS` | `LoadTest12345!` | Password for the test user above. |

Example overriding all three:
```bash
k6 run \
  -e API_BASE=http://staging.silklens.app:8000 \
  -e LOAD_TEST_EMAIL=bench@silklens.app \
  -e LOAD_TEST_PASS=Bench12345! \
  tests/load/read-load.js
```

---

## CI integration

Load tests are triggered via `workflow_dispatch` in `.github/workflows/quality.yml`
(manual trigger only — they are too slow and environment-specific to run on every PR).

Trigger from the GitHub Actions tab or with the `gh` CLI:
```bash
gh workflow run quality.yml -f test_type=load-smoke
```

The smoke test is also a candidate for a post-deploy check in the CD pipeline
(run after the staging deploy, fail the pipeline if any threshold is breached).

---

## Interpreting results

### Key metrics

| Metric | What it means |
|---|---|
| `http_req_duration` | Round-trip time from k6 sending the request to receiving the full response body. `p(95)` = 95th percentile — 95 % of requests completed within this time. |
| `http_req_failed` | Fraction of requests where k6 got a network error OR a non-2xx status. Note: for `auth-stress.js` this is expected to be high (401s). |
| `errors` | Custom `Rate` metric incremented by the test script whenever a `check()` fails. More specific than `http_req_failed`. |
| `server_errors` | (`auth-stress.js` only) Rate of 5xx responses. Should be near 0 even under stress. |
| `iterations` | Total number of completed VU iterations. Divide by duration to get throughput (req/s per VU). |
| `vus` | Active virtual users at each sample point. |

### Threshold interpretation

A threshold failure means k6 exits with a non-zero code and prints a summary like:

```
FAIL — http_req_duration............: p(95)=1423ms — exceeds 1000ms
```

This tells you the 95th-percentile response time exceeded the budget. Likely causes:
- Database is saturated (check `make logs` and Postgres slow-query log).
- Argon2id work factor too high for the dev box (expected on auth-stress under load).
- A slow query is blocking the request path (run `EXPLAIN ANALYZE` on the heritage list query).

### What "good" looks like on a dev box

On a laptop running `make dev` + `make api-run`:
- Smoke: all checks green, `p(95) < 500 ms`
- Read-load at 20 VUs: `p(95) < 800 ms`, error rate < 0.5 %
- Auth-stress at 5 VUs: `p(95) < 2 s` (Argon2id is intentionally slow), server_errors = 0

Numbers significantly worse than these suggest a regression in query performance,
missing indexes, or a blocking lock. Use `make api-test-cov` and Postgres `pg_stat_activity`
to investigate before assuming the issue is in k6 or the test scripts.

---

## Adding new test scenarios

1. Create a new file in `tests/load/` following the naming convention: `<scope>-<type>.js`
   (e.g. `upload-spike.js`, `search-load.js`).
2. Add a row to the table above.
3. Add a `make load-<scope>` target to the root `Makefile`.
4. Reference it in the CI `quality.yml` `workflow_dispatch` inputs if needed.
