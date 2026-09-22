import { expect, test } from '@playwright/test';

import { signInAsAdmin } from './fixtures';

test.describe('branding', () => {
  test('loads existing branding then PUTs an update', async ({ page }) => {
    await signInAsAdmin(page);
    await page.goto('/branding');

    // Primary color input is pre-populated by the mock.
    const primary = page.locator('input#primary_color');
    await expect(primary).toHaveValue('#1e3a8a');

    const putRequest = page.waitForRequest(
      (req) =>
        req.url().includes('/v1/admin/tenants/') &&
        req.url().endsWith('/branding') &&
        req.method() === 'PUT',
    );

    await primary.fill('#10b981');
    await page.getByRole('button', { name: /save branding/i }).click();
    const request = await putRequest;
    const body = JSON.parse(request.postData() ?? '{}');
    expect(body.primary_color).toBe('#10b981');
  });
});
