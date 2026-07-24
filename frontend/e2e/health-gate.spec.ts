import { test, expect } from '@playwright/test';

test.describe('HealthGate (E2E)', () => {
  test('shows loading state on initial render', async ({ page }) => {
    await page.goto('/');
    await expect(page.getByText(/システムを初期化中/)).toBeVisible({ timeout: 5_000 });
  });

  test('backend unreachable shows error state', async ({ page }) => {
    await page.goto('/');
    await page.waitForTimeout(15_000);
    await expect(page.getByText(/バックエンドサーバーに接続できません/)).toBeVisible();
  });
});
