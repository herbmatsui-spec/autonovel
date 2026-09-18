// E2E test for manuscript count functionality
// シナリオ: ルビ挿入 → カウント切替 → 目標判定 → 永続化の実操作確認

import { test, expect } from '@playwright/test';

test.describe('Manuscript Count E2E Tests', () => {
  test.beforeEach(async ({ page }) => {
    await page.goto('/editor');
    // テスト用作品・チャプターの作成や選択
    // ここでは既存のテスト環境に合わせて調整が必要
  });

  test('ルビ挿入 → 3モード切替 → 目標判定 → 永続化の全フロー', async ({ page }) => {
    // 1. エディタで本文入力
    await page.fill('[data-testid="editor-textarea"]', '吾輩は猫である。');
    
    // 2. ルビ挿入ボタンで <ruby>薔薇<rt>ばら</rt></ruby> 挿入
    await page.click('[data-testid="btn-insert-ruby"]');
    // または直接入力: 吾輩は<ruby>猫<rt>ねこ</rt></ruby>である
    await page.fill('[data-testid="editor-textarea"]', '吾輩は<ruby>猫<rt>ねこ</rt></ruby>である。');
    
    // 3. バッジ「本文」モードでカウント確認 (ルビ除外: 「吾輩は猫である。」= 10文字)
    await expect(page.locator('[data-testid="manuscript-count-value"]')).toContainText('本文');
    await expect(page.locator('[data-testid="manuscript-count-value"]')).toContainText('10 字');
    
    // 4. 「ルビ込み」切替 → カウント増加確認 (「吾輩は猫(ねこ)である。」= 13文字)
    await page.click('[data-testid="mode-with-ruby-btn"]');
    await expect(page.locator('[data-testid="mode-with-ruby-btn"]')).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('[data-testid="manuscript-count-value"]')).toContainText('ルビ込');
    await expect(page.locator('[data-testid="manuscript-count-value"]')).toContainText('13 字');
    
    // 5. 「出版用」切替 → 400字詰め枚数表示確認
    await page.click('[data-testid="mode-publishing-btn"]');
    await expect(page.locator('[data-testid="mode-publishing-btn"]')).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('[data-testid="manuscript-count-value"]')).toContainText('原稿');
    await expect(page.locator('[data-testid="manuscript-count-value"]')).toContainText('枚');
    
    // 6. 目標プリセット「新人賞標準」選択 → 進捗バー 90% で黄色警告確認
    // 12000字目標に対して10800字入力
    await page.fill('[data-testid="editor-textarea"]', 'あ'.repeat(10800));
    await expect(page.locator('[data-testid="preset-select"]')).toHaveValue('shousetsu-gekkan');
    await expect(page.locator('[data-testid="target-progress-text"]')).toContainText('90%');
    // プログレスバーの色が黄色（警告）であることを確認
    const progressBar = page.locator('[role="progressbar"] >> div');
    await expect(progressBar).toHaveCSS('background-color', 'rgb(234, 179, 8)'); // #eab308
    
    // 7. さらに入力→目標超過で赤表示確認
    await page.fill('[data-testid="editor-textarea"]', 'あ'.repeat(12001));
    await expect(page.locator('[data-testid="target-progress-text"]')).toContainText('目標超過');
    await expect(progressBar).toHaveCSS('background-color', 'rgb(239, 68, 68)'); // #ef4444
    
    // 8. プレビュー開く → 同一カウント・同一モード表示確認
    await page.click('[data-testid="tab-preview"]');
    await expect(page.locator('[data-testid="editor-preview"]')).toBeVisible();
    await expect(page.locator('[data-testid="manuscript-count-value"]')).toContainText('目標超過');
    await expect(page.locator('[data-testid="mode-publishing-btn"]')).toHaveAttribute('aria-pressed', 'true');
    
    // 9. エディタタブに戻る
    await page.click('[data-testid="tab-edit"]');
    
    // 10. ページリロード → モード・プリセット復元確認
    await page.reload();
    await expect(page.locator('[data-testid="mode-publishing-btn"]')).toHaveAttribute('aria-pressed', 'true');
    await expect(page.locator('[data-testid="preset-select"]')).toHaveValue('shousetsu-gekkan');
  });

  test('カスタム目標設定の動作確認', async ({ page }) => {
    await page.fill('[data-testid="editor-textarea"]', 'あ'.repeat(5000));
    
    // カスタムプリセットを選択
    await page.selectOption('[data-testid="preset-select"]', 'custom');
    
    // カスタム目標文字数入力
    const customInput = page.locator('input[type="number"]');
    await expect(customInput).toBeVisible();
    await customInput.fill('8000');
    
    // 進捗バーが 5000/8000 = 62.5% になることを確認
    await expect(page.locator('[data-testid="target-progress-text"]')).toContainText('62%');
  });

  test('電撃文庫プリセットで上限超過表示', async ({ page }) => {
    // 400字×100枚 = 40000字目標、上限100枚
    await page.selectOption('[data-testid="preset-select"]', 'dengeki-bunko');
    await page.fill('[data-testid="editor-textarea"]', 'あ'.repeat(41000));
    
    // 103枚で上限超過表示
    await expect(page.locator('[data-testid="target-progress-text"]')).toContainText('上限 100枚 超過');
    await expect(page.locator('[data-testid="target-progress-text"]')).toContainText('現在 103枚');
  });

  test('キーボード操作でのアクセシビリティ確認', async ({ page }) => {
    // Tab キーでバッジのセグメントセレクタにフォーカス
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab');
    await page.keyboard.press('Tab'); // バッジの最初のボタンにフォーカス
    
    // Enter/Space でモード切替可能
    await page.keyboard.press('Enter');
    await expect(page.locator('[data-testid="mode-with-ruby-btn"]')).toHaveAttribute('aria-pressed', 'true');
    
    // 矢印キーで次のボタンへ
    await page.keyboard.press('ArrowRight');
    await page.keyboard.press('Enter');
    await expect(page.locator('[data-testid="mode-publishing-btn"]')).toHaveAttribute('aria-pressed', 'true');
    
    // プリセットセレクトもキーボード操作可能
    await page.keyboard.press('Tab');
    await page.keyboard.press('Enter');
    await page.keyboard.press('ArrowDown');
    await page.keyboard.press('Enter');
    await expect(page.locator('[data-testid="preset-select"]')).toHaveValue('shousetsu-subaru');
  });
});