import { test, expect } from '@playwright/test';

test.describe('Catalog resolver E2E', () => {
  test.skip(!process.env.E2E_WITH_AUTH, 'Requires E2E_WITH_AUTH=1');

  test('catalog copilot page loads', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email/i).fill(process.env.E2E_EMAIL ?? 'admin@example.com');
    await page.getByLabel(/password/i).fill(process.env.E2E_PASSWORD ?? 'password123');
    await page.getByRole('button', { name: /sign in/i }).click();
    await page.goto('/catalog-copilot');
    await expect(page.getByRole('heading', { name: 'Catalog Copilot' })).toBeVisible();
    await expect(page.getByRole('button', { name: 'Reindex catalog' })).toBeVisible();
  });
});
