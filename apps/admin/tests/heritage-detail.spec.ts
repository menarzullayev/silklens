import { expect, test } from '@playwright/test';

import { signInAsAdmin } from './fixtures';

test.describe('heritage detail', () => {
  test('renders heritage detail page', async ({ page }) => {
    await signInAsAdmin(page);
    // FAKE_HERITAGE_PAGE.items[0] is served for any GET /v1/heritage/{pub_id}.
    // Its English name is "Registan".
    await page.goto('/heritage/her_registan');

    // PageHeader renders the heritage name as the h1 title.
    await expect(
      page.getByRole('heading', { name: /registan/i }),
    ).toBeVisible();
  });

  test('shows overview tab content', async ({ page }) => {
    await signInAsAdmin(page);
    await page.goto('/heritage/her_registan');

    // The overview tab is selected by default (defaultValue="overview").
    // The mock object has status="published" and country_code="UZ" — both
    // should appear in the HeritageForm pre-populated values.
    await expect(
      page.getByRole('tab', { name: /overview|umumiy/i }),
    ).toHaveAttribute('data-state', 'active');

    // Status badge rendered in the PageHeader actions area.
    await expect(page.getByText('published')).toBeVisible();
  });

  test('navigates between tabs', async ({ page }) => {
    await signInAsAdmin(page);
    await page.goto('/heritage/her_registan');

    // Switch to Translations tab.
    await page.getByRole('tab', { name: /translations|tarjimalar/i }).click();
    // TranslationsMatrix renders a Card with title "Translation coverage".
    await expect(page.getByText('Translation coverage')).toBeVisible();

    // Switch to Revisions tab.
    await page.getByRole('tab', { name: /revisions|tahrirlar/i }).click();
    // RevisionsTimeline renders a Card with title "Revision history".
    // The mock returns an empty revisions list, so the empty-state message is shown.
    await expect(page.getByText('Revision history')).toBeVisible();
  });
});
