import { expect, test } from '@playwright/test';

/**
 * SILK-0167: Minimal login-page smoke test stub.
 *
 * Full credentials flow lives in `auth.spec.ts` (uses the mocked backend
 * fixture). This file exists so future E2E expansion has a dedicated home
 * for login-screen UI assertions (form validation, password visibility
 * toggle, error banner copy) without growing the auth-flow test.
 */
test.describe('login page', () => {
  test('renders the sign-in form', async ({ page }) => {
    await page.goto('/login');
    await expect(page).toHaveURL(/\/login/);
    // Sign-in heading is locale-dependent; just assert the form exists.
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    await expect(page.locator('button[type="submit"]').first()).toBeVisible();
  });
});
