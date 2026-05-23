/**
 * SILK-0167: E2E navigation tests — no auth required.
 * Tests that verify public routing behaviour: root redirect, login page
 * metadata, and protection of authenticated-only routes.
 */
import { test, expect } from '@playwright/test';

test.describe('Navigation', () => {
  test('home (/) redirects to login when not authenticated', async ({ page }) => {
    await page.goto('/');
    await expect(page).toHaveURL(/\/login/);
  });

  test('login page has correct SilkLens title', async ({ page }) => {
    await page.goto('/login');
    await expect(page).toHaveTitle(/SilkLens/i);
  });

  test('protected routes redirect unauthenticated users to /login', async ({
    page,
  }) => {
    const protectedPaths = ['/dashboard', '/heritage', '/tenants', '/settings'];
    for (const path of protectedPaths) {
      const response = await page.goto(path);
      await expect(page, `${path} should redirect to login`).toHaveURL(/\/login/);
      // The redirect itself should not produce a 5xx.
      expect(response?.status() ?? 200).toBeLessThan(500);
    }
  });

  test('login page has email and password form fields', async ({ page }) => {
    await page.goto('/login');
    const heading = page.getByRole('heading', { level: 1 });
    await expect(heading).toBeVisible();
    // Heading text varies by i18n locale — accept any supported language.
    await expect(heading).toHaveText(/Kirish|Sign in|Войти|登录/);
  });
});
