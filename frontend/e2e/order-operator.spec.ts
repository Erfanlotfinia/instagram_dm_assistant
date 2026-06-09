import { test, expect } from '@playwright/test';

test.describe('Order operator controls', () => {
  test.skip(!process.env.E2E_WITH_AUTH, 'Set E2E_WITH_AUTH=1 with a seeded stack to run');

  test('order detail page loads', async ({ page }) => {
    await page.goto('/login');
    await page.getByLabel(/email/i).fill('admin@test.com');
    await page.getByLabel(/password/i).fill('password123');
    await page.getByRole('button', { name: /sign in|login/i }).click();
    await page.goto('/orders');
    await expect(page.getByText(/orders/i).first()).toBeVisible();
  });
});
