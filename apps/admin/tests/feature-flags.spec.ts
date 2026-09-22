import { expect, test } from '@playwright/test';

import { API_BASE, FAKE_FEATURE_FLAGS, signInAsAdmin } from './fixtures';

test.describe('feature flags', () => {
  test('renders feature flags list', async ({ page }) => {
    await signInAsAdmin(page);
    await page.goto('/feature-flags');

    // English: "Feature flags", Uzbek: "Xususiyat bayroqlari".
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(
      /feature flags|xususiyat bayroqlari|флаги функций|功能标志/i,
    );

    // The single mock flag key must appear in the table.
    await expect(page.getByText('ai.live_translation')).toBeVisible();
  });

  test('flag toggle calls PUT /v1/admin/feature-flags/{key}', async ({ page }) => {
    // Register the PUT mock before signing in so it takes precedence over the
    // catch-all 404 fallback in mockBackend.
    await page.route(`${API_BASE}/v1/admin/feature-flags/*`, async (route) => {
      if (route.request().method() === 'PUT') {
        return route.fulfill({
          json: { ...FAKE_FEATURE_FLAGS[0], enabled: false },
        });
      }
      return route.fallback();
    });

    await signInAsAdmin(page);
    await page.goto('/feature-flags');

    const putRequest = page.waitForRequest(
      (req) =>
        req.url().includes('/v1/admin/feature-flags/') && req.method() === 'PUT',
    );

    // The switch is rendered with aria-label "Toggle ai.live_translation".
    const toggle = page.getByRole('switch', {
      name: /toggle ai\.live_translation/i,
    });
    await expect(toggle).toBeVisible();
    await toggle.click();
    await putRequest;
  });

  test('description text is shown', async ({ page }) => {
    await signInAsAdmin(page);
    await page.goto('/feature-flags');

    // The description column renders the raw description string from the API.
    await expect(
      page.getByText('Stream translations as user types'),
    ).toBeVisible();
  });
});
