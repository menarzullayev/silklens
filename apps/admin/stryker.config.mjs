/**
 * Stryker mutation testing configuration — SilkLens Admin
 *
 * Scope: the 5 pure-logic modules tested by the Vitest unit suite.
 * Each mutation (operator change, boundary flip, statement removal, …) is
 * run through `vitest run`; survived mutations indicate test gaps.
 *
 * Thresholds:
 *   break ≥ 50 — CI fails below this score (hard floor)
 *   low   ≥ 60 — warning zone
 *   high  ≥ 80 — green zone
 *
 * Reference: https://stryker-mutator.io/docs/stryker-js/configuration/
 */

/** @type {import('@stryker-mutator/api/core').PartialStrykerOptions} */
export default {
  packageManager: 'pnpm',

  // Reporter set: clear-text summary in CI, HTML report locally for drill-down.
  reporters: ['html', 'clear-text', 'progress'],

  testRunner: 'vitest',
  vitest: {
    configFile: 'vitest.config.ts',
  },

  // Mutate only the 5 pure-logic source files — not test files, not mocks.
  mutate: [
    'src/lib/utils.ts',
    'src/lib/api/errors.ts',
    'src/lib/rbac/permissions.ts',
    'src/lib/tenant/tenant.ts',
    'src/lib/i18n/config.ts',
    // Exclude the mock stub — not production code.
    '!src/__mocks__/**',
  ],

  thresholds: {
    high: 80,
    low: 60,
    break: 50,
  },

  // Kill mutations that don't complete within 10s (generous for Vitest in-process).
  timeoutMS: 10000,
  timeoutFactor: 1.5,

  // Parallelism: 2 concurrent workers keeps CI memory usage bounded.
  // Increase locally: `pnpm stryker run --concurrency 4`
  concurrency: 2,

  // HTML report written here; add to .gitignore.
  htmlReporter: {
    fileName: 'reports/mutation/index.html',
  },
};
