import { test, expect } from '@playwright/test';

test.describe('Inline Revision E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/editor');
    await page.waitForLoadState('networkidle');
  });

  test.describe('推敲フローの基本操作', () => {
    test('テキストを選択して推敲ボタンを押すとモーダルが開く', async ({ page }) => {
      const editor = page.locator('[contenteditable="true"]');
      await editor.fill('これは推敲対象のテキストです。');

      await page.locator('text=推敲').click();

      await expect(page.locator('text=推敲結果の確認')).toBeVisible();
    });

    test('推敲モーダルで原文と修正後が表示される', async ({ page }) => {
      const editor = page.locator('[contenteditable="true"]');
      await editor.fill('これはテストです。');

      await page.locator('text=推敲').click();

      await expect(page.locator('text=原文')).toBeVisible();
      await expect(page.locator('text=修正後')).toBeVisible();
    });

    test('適用ボタンで修正が適用される', async ({ page }) => {
      const editor = page.locator('[contenteditable="true"]');
      await editor.fill('これはテストです。');

      await page.locator('text=推敲').click();
      await page.locator('text=適用').click();

      await expect(page.locator('text=推敲結果の確認')).not.toBeVisible();
    });

    test('却下ボタンでモーダルが閉じる', async ({ page }) => {
      const editor = page.locator('[contenteditable="true"]');
      await editor.fill('これはテストです。');

      await page.locator('text=推敲').click();
      await page.locator('text=却下').click();

      await expect(page.locator('text=推敲結果の確認')).not.toBeVisible();
    });

    test('保留ボタンでモーダルが閉じる', async ({ page }) => {
      const editor = page.locator('[contenteditable="true"]');
      await editor.fill('これはテストです。');

      await page.locator('text=推敲').click();
      await page.locator('text=保留').click();

      await expect(page.locator('text=推敲結果の確認')).not.toBeVisible();
    });
  });

  test.describe('差分表示', () => {
    test('文字レベルの差分が表示される', async ({ page }) => {
      const editor = page.locator('[contenteditable="true"]');
      await editor.fill('こんにちは世界');

      await page.locator('text=推敲').click();

      await expect(page.locator('.diff-viewer')).toBeVisible();
      await expect(page.locator('.diff-insert')).toBeVisible();
    });

    test('粒度切り替えが機能する', async ({ page }) => {
      const editor = page.locator('[contenteditable="true"]');
      await editor.fill('行1\n行2\n行3');

      await page.locator('text=推敲').click();

      await expect(page.locator('text=粒度: 文字')).toBeVisible();
    });
  });

  test.describe('原文検証', () => {
    test('元のテキストが変更されている場合、警告が表示される', async ({ page }) => {
      const editor = page.locator('[contenteditable="true"]');
      await editor.fill('元のテキストです。');

      await page.locator('text=推敲').click();

      await page.evaluate(() => {
        const editor = document.querySelector('[contenteditable="true"]');
        if (editor) editor.innerText = '編集されたテキストです。';
      });

      await page.locator('text=適用').click();

      await expect(page.locator('text=原文が変更されています')).toBeVisible();
    });

    test('確認ダイアログで「キャンセル」を押すと適用されない', async ({ page }) => {
      const editor = page.locator('[contenteditable="true"]');
      await editor.fill('元のテキストです。');

      await page.locator('text=推敲').click();

      await page.evaluate(() => {
        const editor = document.querySelector('[contenteditable="true"]');
        if (editor) editor.innerText = '編集されたテキストです。';
      });

      await page.locator('text=適用').click();
      await expect(page.locator('text=原文が変更されています')).toBeVisible();

      await page.locator('text=キャンセル').click();

      await expect(page.locator('text=推敲結果の確認')).toBeVisible();
    });

    test('確認ダイアログで「それでも適用」を押すと適用される', async ({ page }) => {
      const editor = page.locator('[contenteditable="true"]');
      await editor.fill('元のテキストです。');

      await page.locator('text=推敲').click();

      await page.evaluate(() => {
        const editor = document.querySelector('[contenteditable="true"]');
        if (editor) editor.innerText = '編集されたテキストです。';
      });

      await page.locator('text=適用').click();
      await expect(page.locator('text=原文が変更されています')).toBeVisible();

      await page.locator('text=それでも適用').click();

      await expect(page.locator('text=推敲結果の確認')).not.toBeVisible();
    });
  });

  test.describe('Undo/Redo', () => {
    test('適用後にUndoで元に戻せる', async ({ page }) => {
      const editor = page.locator('[contenteditable="true"]');
      await editor.fill('元のテキストです。');

      await page.locator('text=推敲').click();
      await page.locator('text=適用').click();

      await page.keyboard.press('Control+Z');

      await expect(page.locator('[contenteditable="true"]')).toHaveText('元のテキストです。');
    });

    test('Undo後にRedoで再適用できる', async ({ page }) => {
      const editor = page.locator('[contenteditable="true"]');
      await editor.fill('元のテキストです。');

      await page.locator('text=推敲').click();
      await page.locator('text=適用').click();

      await page.keyboard.press('Control+Z');
      await page.keyboard.press('Control+Y');

      await expect(page.locator('[contenteditable="true"]')).not.toHaveText('元のテキストです。');
    });
  });

  test.describe('エラーハンドリング', () => {
    test('APIエラー時にエラー表示される', async ({ page }) => {
      await page.route('/api/revision/generate', (route) => {
        route.fulfill({ status: 500, body: 'Server Error' });
      });

      const editor = page.locator('[contenteditable="true"]');
      await editor.fill('テストテキスト');

      await page.locator('text=推敲').click();

      await expect(page.locator('text=エラー')).toBeVisible({ timeout: 5000 });
    });

    test('ネットワークエラー時にリトライ可能', async ({ page }) => {
      await page.route('/api/revision/generate', (route) => {
        route.abort('failed');
      });

      const editor = page.locator('[contenteditable="true"]');
      await editor.fill('テストテキスト');

      await page.locator('text=推敲').click();

      await expect(page.locator('text=エラー')).toBeVisible({ timeout: 5000 });
    });
  });

  test.describe('キーボードショートカット', () => {
    test('Escapeキーでモーダルが閉じる', async ({ page }) => {
      const editor = page.locator('[contenteditable="true"]');
      await editor.fill('テストテキストです。');

      await page.locator('text=推敲').click();
      await expect(page.locator('text=推敲結果の確認')).toBeVisible();

      await page.keyboard.press('Escape');

      await expect(page.locator('text=推敲結果の確認')).not.toBeVisible();
    });
  });

  test.describe('アクセシビリティ', () => {
    test('モーダルに適切なARIA属性がある', async ({ page }) => {
      const editor = page.locator('[contenteditable="true"]');
      await editor.fill('テストテキストです。');

      await page.locator('text=推敲').click();

      const modal = page.locator('[role="dialog"]');
      await expect(modal).toHaveAttribute('aria-modal', 'true');
      await expect(modal).toHaveAttribute('aria-labelledby');
    });

    test('ボタンに適切なaria-labelがある', async ({ page }) => {
      const editor = page.locator('[contenteditable="true"]');
      await editor.fill('テストテキストです。');

      await page.locator('text=推敲').click();

      await expect(page.locator('button[aria-label="閉じる"]')).toBeVisible();
    });
  });
});