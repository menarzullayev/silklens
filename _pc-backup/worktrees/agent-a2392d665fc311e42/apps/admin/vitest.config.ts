/**
 * Vitest configuration for SilkLens Admin unit tests.
 *
 * Scope: pure-logic modules under src/lib/ that have zero Next.js
 * framework dependencies (or whose framework-dependent exports are
 * skipped / mocked in individual test files).
 *
 * Playwright handles E2E; this layer covers the business-logic core
 * (utils, error hierarchy, RBAC, tenant helpers, i18n config).
 */
import path from 'path';
import { defineConfig } from 'vitest/config';

export default defineConfig({
  test: {
    // No globals — each test file uses explicit vitest imports.
    globals: false,
    // Node environment: no DOM needed for pure-logic tests.
    environment: 'node',
    include: ['src/**/*.test.ts', 'src/**/*.test.tsx'],
    // next/headers is a server-only Next.js module; Vitest cannot resolve it
    // in a Node environment. Provide an auto-mock so any module that imports
    // it (e.g. tenant.ts) doesn't break when only the pure exports are under
    // test. Individual test files can refine the mock via vi.mock().
    server: {
      deps: {
        inline: [],
      },
    },
  },
  resolve: {
    alias: {
      // Mirror the tsconfig path alias so src/ imports work identically.
      '@': path.resolve(__dirname, './src'),
      // Stub next/headers to prevent import errors in non-Next.js test runner.
      'next/headers': path.resolve(__dirname, 'src/__mocks__/next-headers.ts'),
    },
  },
});
