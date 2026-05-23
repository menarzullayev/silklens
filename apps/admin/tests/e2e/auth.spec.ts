/**
 * SILK-0167: E2E auth flow tests — no mock backend required.
 * These tests exercise the public auth surface: login form rendering,
 * invalid credential rejection, and unauthenticated redirect behaviour.
 *
 * For tests that need a mocked backend (full sign-in → dashboard), see
 * the parent `tests/auth.spec.ts` which uses the `mockBackend` fixture.
 */
import { test, expect } from '@playwright/test';

test.describe('Authentication', () => {
  test('login page loads and shows form fields', async ({ page }) => {
    await page.goto('/login');
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]').first()).toBeVisible();
  });

  test('login page has correct title', async ({ page }) => {
    await page.goto('/login');
    await expect(page).toHaveTitle(/SilkLens/i);
  });

  test('invalid credentials keeps user on login page', async ({ page }) => {
    await page.goto('/login');
    await page.fill('input[type="email"]', 'invalid@test.com');
    await page.fill('input[type="password"]', 'wrongpassword');
    await page.locator('button[type="submit"]').first().click();
    // Should remain on login — no redirect to dashboard on bad credentials.
    await expect(page).toHaveURL(/\/login/);
  });

  test('unauthenticated user is redirected to login from protected route', async ({
    page,
  }) => {
    await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login/);
  });
});
