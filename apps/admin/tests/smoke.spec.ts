import { expect, test } from '@playwright/test';

test.describe('admin panel — smoke', () => {
  test('login page renders title and form fields', async ({ page }) => {
    await page.goto('/login');

    await expect(page).toHaveTitle(/Sign in/i);

    // i18n default is 'uz' → button label is "Kirish". Falls back to English
    // for non-uz locales; cover both.
    const heading = page.getByRole('heading', { level: 1 });
    await expect(heading).toBeVisible();
    await expect(heading).toHaveText(/Kirish|Sign in|Войти|登录/);

    // The credentials form must be present.
    await expect(page.locator('input[type="email"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();

    // Sign-in submit button.
    const submit = page.locator('button[type="submit"]').first();
    await expect(submit).toBeVisible();
  });

  test('protected routes redirect anonymous users to /login', async ({ page }) => {
    const response = await page.goto('/dashboard');
    await expect(page).toHaveURL(/\/login/);
    expect(response?.status()).toBeLessThan(500);
  });
});
