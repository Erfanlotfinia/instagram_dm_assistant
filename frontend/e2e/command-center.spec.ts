import { test, expect } from '@playwright/test';

test.describe('Command center shell E2E', () => {
  test.skip(!process.env.E2E_WITH_AUTH, 'Requires E2E_WITH_AUTH=1');

  async function login(page: import('@playwright/test').Page) {
    await page.goto('/login');
    await page.getByLabel(/email/i).fill(process.env.E2E_EMAIL ?? 'admin@example.com');
    await page.getByLabel(/password/i).fill(process.env.E2E_PASSWORD ?? 'password123');
    await page.getByRole('button', { name: /sign in/i }).click();
    await expect(page).toHaveURL(/\/$/);
  }

  test('command palette navigates to the inbox', async ({ page }) => {
    await login(page);
    await page.keyboard.press('Control+k');
    await expect(page.getByPlaceholder('Search pages and actions…')).toBeVisible();
    await page.getByPlaceholder('Search pages and actions…').fill('inbox');
    await page.keyboard.press('Enter');
    await expect(page).toHaveURL(/\/inbox/);
    await expect(page.getByRole('heading', { name: 'Unified Inbox' })).toBeVisible();
  });

  test('handoff queue is reachable from the sidebar', async ({ page }) => {
    await login(page);
    await page.getByRole('link', { name: 'Handoffs' }).click();
    await expect(page).toHaveURL(/\/handoffs/);
    await expect(page.getByRole('heading', { name: 'Human Handoff Queue' })).toBeVisible();
  });

  test('legacy conversation route redirects to the inbox', async ({ page }) => {
    await login(page);
    await page.goto('/conversations');
    await expect(page).toHaveURL(/\/inbox/);
  });
});
