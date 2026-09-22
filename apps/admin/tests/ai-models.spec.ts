import { expect, test } from '@playwright/test';

import { signInAsAdmin } from './fixtures';

test.describe('ai models', () => {
  test('models tab renders rows from /v1/ai/models', async ({ page }) => {
    await signInAsAdmin(page);
    await page.goto('/ai-models');
    await expect(page.getByText('gpt-4o')).toBeVisible();
    await expect(page.getByText('claude-sonnet')).toBeVisible();
  });

  test('fallback chains tab shows a chain', async ({ page }) => {
    await signInAsAdmin(page);
    await page.goto('/ai-models');
    await page.getByRole('tab', { name: /fallback chains/i }).click();
    await expect(page.getByText('Default LLM chain')).toBeVisible();
  });
});
