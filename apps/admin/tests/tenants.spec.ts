import { expect, test } from '@playwright/test';

import { signInAsAdmin } from './fixtures';

test.describe('tenants management', () => {
  test('list page shows mocked tenants', async ({ page }) => {
    await signInAsAdmin(page);
    await page.goto('/tenants');
    await expect(page.getByText('silklens', { exact: false })).toBeVisible();
    await expect(page.getByText('acme', { exact: false })).toBeVisible();
  });

  test('create tenant dialog posts to /v1/admin/tenants', async ({ page }) => {
    await signInAsAdmin(page);
    await page.goto('/tenants');
    await page.getByRole('button', { name: /new tenant/i }).click();

    const createRequest = page.waitForRequest(
      (req) =>
        req.url().endsWith('/v1/admin/tenants') && req.method() === 'POST',
    );

    await page.locator('input#slug').fill('demo-tenant');
    // Fill the English display name tab.
    await page.locator('input').nth(1).fill('Demo Tenant');
    await page.getByRole('button', { name: /^create$/i }).click();
    await createRequest;
  });
});
