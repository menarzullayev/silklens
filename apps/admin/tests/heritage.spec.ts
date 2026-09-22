import { expect, test } from '@playwright/test';

import { signInAsAdmin } from './fixtures';

test.describe('heritage list', () => {
  test('renders rows fetched from the backend', async ({ page }) => {
    await signInAsAdmin(page);
    await page.goto('/heritage');

    // The seeded mock has two entries — both should appear.
    await expect(page.getByRole('link', { name: 'Registan' })).toBeVisible();
    await expect(page.getByRole('link', { name: 'Itchan Kala' })).toBeVisible();
  });

  test('filter dropdown is wired (kind selector renders options)', async ({ page }) => {
    await signInAsAdmin(page);
    await page.goto('/heritage');

    // Open the "Filter by kind" combobox.
    await page.getByLabel('Filter by kind').click();
    await expect(page.getByRole('option', { name: 'Monument' })).toBeVisible();
  });
});
