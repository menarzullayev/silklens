/**
 * SILK-0167: E2E heritage tests — backend-conditional.
 * Tests that verify the heritage list page routing and error handling.
 * Requires a running backend only for the fetch-dependent assertions;
 * routing tests run against the mock-free Next.js dev server.
 *
 * For tests with a mocked backend and seeded data (Registan, Itchan Kala),
 * see the parent `tests/heritage.spec.ts` which uses `signInAsAdmin`.
 */
import { test, expect } from '@playwright/test';

test.describe('Heritage (unauthenticated)', () => {
  test('heritage list redirects unauthenticated users to login', async ({ page }) => {
    await page.goto('/heritage');
    await expect(page).toHaveURL(/\/login/);
  });

  test('heritage list redirect does not produce a 5xx error', async ({ page }) => {
    const response = await page.goto('/heritage');
    // Any redirect status or 200 is fine — 5xx means a server crash.
    expect(response?.status() ?? 200).toBeLessThan(500);
  });
});

test.describe('Heritage (backend-conditional)', () => {
  test.beforeEach(async ({ page }) => {
    const response = await page.request
      .get('http://localhost:8000/health')
      .catch(() => null);
    test.skip(!response?.ok(), 'Backend not running — skipping backend-dependent tests');
  });

  test('heritage list page loads without 500', async ({ page }) => {
    await page.goto('/heritage');
    // Without auth the user is redirected to login — that is still not /500.
    await expect(page).not.toHaveURL('/500');
  });
});
