import { expect, test } from '@playwright/test';

import { signInAsAdmin } from './fixtures';

test.describe('moderation', () => {
  test('renders moderation queue page', async ({ page }) => {
    await signInAsAdmin(page);
    await page.goto('/moderation');

    // The ModerationPage uses a hard-coded title string: "Moderation".
    // No i18n key is used here — the title is literal in the source.
    await expect(page.getByRole('heading', { level: 1 })).toHaveText(
      /moderation/i,
    );
  });

  test('shows queue stat cards', async ({ page }) => {
    await signInAsAdmin(page);
    await page.goto('/moderation');

    // mockBackend returns 404 for /v1/admin/moderation* so fetchQueue falls
    // back to { items: [], total: 0 }.  The four stat cards still render with
    // their labels — they just show 0 counts.
    await expect(page.getByText('Pending Reviews')).toBeVisible();
    await expect(page.getByText('Flagged Content')).toBeVisible();
  });

  test('renders heritage review queue card', async ({ page }) => {
    await signInAsAdmin(page);
    await page.goto('/moderation');

    // The CardTitle inside the heritage queue section is "Heritage Review Queue".
    await expect(page.getByText('Heritage Review Queue')).toBeVisible();
  });
});
