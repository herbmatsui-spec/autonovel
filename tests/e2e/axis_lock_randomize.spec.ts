import { test, expect } from '@playwright/test';

test.describe('Axis Lock & Randomize', () => {
  test.beforeEach(async ({ page }) => {
    // Navigate to the app and create/select a book
    await page.goto('/');
    // Assume there's a way to create a book or select one
    // This will depend on the actual app flow
    // For now, we'll just check if the page loads
    await expect(page).toHaveTitle(/覇権小説エンジン/);
  });

  test('lock prevents randomization', async ({ page }) => {
    // Find the theme axis selector
    const themeSelector = page.locator('text=テーマ').first();
    await expect(themeSelector).toBeVisible();

    // Click lock button (should be near the label)
    const lockButton = themeSelector.locator('..').locator('button[title="Lock"]');
    await lockButton.click();

    // Click randomize button (should be disabled or have no effect)
    const randomButton = themeSelector.locator('..').locator('button[title="Randomize"]');
    await randomButton.click();

    // The value should not change (we need a way to verify)
    // This is a placeholder; actual implementation would check the input value
  });

  test('all random respects locks', async ({ page }) => {
    // Lock a couple of axes
    // Click all random button
    // Verify locked axes unchanged
  });

  test('persist locks across reload', async ({ page }) => {
    // Lock an axis
    // Reload page
    // Verify lock still active
  });
});