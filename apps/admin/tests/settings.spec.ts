import { expect, test } from '@playwright/test';

import { API_BASE, FAKE_SYSTEM_SETTINGS, signInAsAdmin } from './fixtures';

test.describe('system settings', () => {
  test('renders settings list', async ({ page }) => {
    await signInAsAdmin(page);
    await page.goto('/settings');

    // The page header uses the i18n key "settings.title".
    // English: "System settings", Uzbek: "Tizim sozlamalari".
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(
      /system settings|tizim sozlamalari|настройки системы|系统设置/i,
    );

    // The mock returns two settings; the first key must appear in the tree.
    await expect(page.getByText('ai.default_model')).toBeVisible();
  });

  test('renders grouped settings in tabs', async ({ page }) => {
    await signInAsAdmin(page);
    await page.goto('/settings');

    // SettingsTree groups by key prefix. With FAKE_SYSTEM_SETTINGS we get two
    // prefixes: "ai" and "moderation". Both tab triggers should be present.
    await expect(page.getByRole('tab', { name: /^ai/i })).toBeVisible();
    await expect(page.getByRole('tab', { name: /^moderation/i })).toBeVisible();

    // There should be at least one editable input/textarea/number input visible
    // because neither of the fake settings is a bool or secret type.
    await expect(page.locator('input').first()).toBeVisible();
  });

  test('PUT /v1/admin/system-settings on save', async ({ page }) => {
    // Add the PUT handler before signInAsAdmin so it is available through the
    // shared mockBackend wildcard already installed inside signInAsAdmin.
    await page.route(`${API_BASE}/v1/admin/system-settings`, async (route) => {
      if (route.request().method() === 'PUT') {
        return route.fulfill({ json: FAKE_SYSTEM_SETTINGS[0] });
      }
      // Fall through to next handler (GET is already handled).
      return route.fallback();
    });

    await signInAsAdmin(page);
    await page.goto('/settings');

    const putRequest = page.waitForRequest(
      (req) =>
        req.url().endsWith('/v1/admin/system-settings') && req.method() === 'PUT',
    );

    // The first "Save" button inside the ai.default_model row.
    await page.getByRole('button', { name: /^save$/i }).first().click();
    await putRequest;
  });
});
