import { test, expect } from '@playwright/test';

test.describe('整合性チェック & ワークスペース', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/');
    // Assume there's a way to create/select a book
    // This will depend on the actual app flow
    await page.waitForLoadState('networkidle');
  });

  test('整合性チェックタブが表示され、チェック実行できる', async ({ page }) => {
    // Navigate to a book workspace (assuming book 1 exists)
    await page.goto('/book/1/theme');
    await page.waitForLoadState('networkidle');

    // Click the '整合性' tab
    await page.click('button:has-text("整合性")');
    await expect(page.locator('text=整合性チェック結果')).toBeVisible();

    // Click recheck button
    await page.click('button:has-text("再チェック")');
    await page.waitForLoadState('networkidle');
    // Should show findings (could be empty)
    await expect(page.locator('text=高, text=中, text=低')).toBeVisible({ timeout: 10000 });
  });

  test('ワークスペースタブでファイル編集・保存', async ({ page }) => {
    await page.goto('/book/1/theme');
    await page.waitForLoadState('networkidle');

    // Click 'ワークスペース' tab
    await page.click('button:has-text("ワークスペース")');
    await expect(page.locator('button:has-text("SOUL.md")')).toBeVisible();

    // Switch to WORLD.md
    await page.click('button:has-text("WORLD.md")');
    await expect(page.locator('textarea')).toBeVisible();

    // Edit content
    await page.fill('textarea', '# 世界観\n\n## 概要\nテスト世界観');
    await page.click('button:has-text("保存")');
    await expect(page.locator('text=保存完了')).toBeVisible({ timeout: 5000 });
  });

  test('プリセット出力・読込', async ({ page }) => {
    await page.goto('/book/1/theme');
    await page.waitForLoadState('networkidle');

    await page.click('button:has-text("ワークスペース")');
    // Click export button (need to add to UI)
    // await page.click('button:has-text("プリセット出力")');
    // await expect(page.locator('text=.json')).toBeVisible();
  });
});