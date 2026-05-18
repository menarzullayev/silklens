import { expect, test } from '@playwright/test';

import { mockBackend, signInAsAdmin } from './fixtures';

test.describe('auth flow', () => {
  test('credentials login posts to /v1/auth/login and lands on dashboard', async ({
    page,
  }) => {
    await mockBackend(page);
    const loginRequest = page.waitForRequest(
      (req) => req.url().endsWith('/v1/auth/login') && req.method() === 'POST',
    );
    await page.goto('/login');
    await page.locator('input[type="email"]').fill('admin@silklens.app');
    await page.locator('input[type="password"]').fill('DemoPassword12345');
    await page.locator('button[type="submit"]').first().click();
    await loginRequest;
    await page.waitForURL((url) => !url.pathname.startsWith('/login'));
    expect(page.url()).toMatch(/\/dashboard/);
  });

  test('signed-in user can navigate to the dashboard overview', async ({ page }) => {
    await signInAsAdmin(page);
    await page.goto('/dashboard');
    // The Overview page header is "Overview" in en, "Bosh sahifa" in uz.
    await expect(
      page.getByRole('heading', { level: 1 }),
    ).toHaveText(/Overview|Bosh sahifa|Обзор|概览/);
  });
});
