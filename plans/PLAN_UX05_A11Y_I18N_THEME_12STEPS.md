# AutoNovel UX改善計画: アクセシビリティ・テーマ・i18n 商用レベル化 (全12ステップ)

**対象**: #9 アクセシビリティ・テーマ・i18n 土台の商用レベル化
**目的**: WCAG AA 達成・多言語対応・テーマ完全対応で法的・ユーザビリティ基礎を確立
**前提**: 既存 `useAppTheme.ts` (dark/light/sepia・OS連動・永続化済)・`index.css:1582-1596` (`prefers-reduced-motion`・`:focus-visible`済)・`index.css:1568-1576` (safe-area・touch-target 44px済)

---

## 📋 ステップ一覧マトリクス

| ステップ | 種別 | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | Config | `src/constants/a11y.ts` | [NEW] WCAG AA 達成に必要なコントラスト比・フォーカス仕様・ARIA パターン定義 |
| **Step 2** | Modify | `src/index.css` | [MODIFY] セピアテーマコントラスト比 4.5:1 達成 (テキスト・ボーダー・フォーカス色調整) |
| **Step 3** | Modify | `src/index.html` | [MODIFY] `lang="ja"` 設定、`meta name="theme-color"` 追加、`viewport user-scalable=yes` |
| **Step 4** | i18n Core | `src/i18n/` | [NEW] i18n 構造作成 (ja/en 辞書・ロケール検出・切替フック・永続化) |
| **Step 5** | Component | `src/components/common/LanguageSwitcher.tsx` | [NEW] ヘッダー配置用言語切替コンポーネント (フラグ・ネイティブ名表示) |
| **Step 6** | Modify | `src/App.tsx` | [MODIFY] `LanguageSwitcher` ヘッダー右端配置、初期ロケール適用 |
| Step 7 | Modify | `src/components/common/Modal.tsx` | [MODIFY] フォーカストラップ強化・`aria-describedby` 対応・Esc 以外の閉じる導線 |
| Step 8 | Modify | `src/components/editor/Editor.tsx` | [MODIFY] エディタ・ツールバー・サイドバーのキーボード操作完全到達・ARIA ラベル付与 |
| Step 9 | Modify | `src/components/generate/SimpleModePanel.tsx` | [MODIFY] 生成UI のライブリージョン・進捗アナウンス・エラー読み上げ対応 |
| Step 10 | Utility | `src/utils/announce.ts` | [NEW] `aria-live` 共通アナウンス関数 (polite/assertive 使い分け) |
| Step 11 | Test | `tests/unit/a11y.test.ts` | [NEW] axe-core 自動検査 + キーボード到達・コントラスト・ARIA 手動チェックリストテスト |
| Step 12 | E2E | `tests/e2e/a11y_i18n.test.ts` | [NEW] Playwright: キーボードのみ操作・スクリーンリーダー模擬・言語切替・テーマ切替全フロー |

---

## 🛠️ 各ステップ詳細手順

### Step 1: アクセシビリティ仕様定義
- **対象ファイル**: `src/constants/a11y.ts` (新規作成)
- **実装内容**:
```typescript
// WCAG 2.1 AA 基準値
export const A11Y_SPEC = {
  contrast: {
    normalText: 4.5,      // 通常テキスト 4.5:1
    largeText: 3.0,       // 大きいテキスト (18pt+/14pt bold) 3:1
    uiComponents: 3.0,    // UI コンポーネント境界 3:1
  },
  focus: {
    outlineWidth: '2px',
    outlineOffset: '2px',
    outlineColor: 'var(--accent-primary)', // 既存 CSS 変数利用
  },
  touchTarget: {
    minSize: 44,          // 44x44px (既存 CSS .touch-target 準拠)
  },
  motion: {
    respectReducedMotion: true, // prefers-reduced-motion: reduce 対応済
  },
  liveRegion: {
    politeDelay: 100,     // ms
    assertiveDelay: 0,
  },
} as const;

// 必須 ARIA パターン (実装チェックリスト用)
export const REQUIRED_ARIA_PATTERNS = [
  'modal: role=dialog, aria-modal, aria-labelledby, focus trap',
  'button: type=button, accessible name',
  'input: label for=id, aria-describedby for errors',
  'live region: aria-live=polite/assertive, aria-atomic',
  'tabpanel: role=tablist/tab/tabpanel, aria-selected, aria-controls',
  'menu: role=menu/menuitem, keyboard navigation',
  'tooltip: role=tooltip, aria-describedby',
] as const;
```
- **検証コマンド**: `npx tsc --noEmit --skipLibCheck src/constants/a11y.ts`
- **期待結果**: 型エラーなし、仕様値参照可能

---

### Step 2: セピアテーマコントラスト修正
- **対象ファイル**: `src/index.css` (修正)
- **変更箇所**: L32-44 (`[data-theme="sepia"]`)
- **実装内容**: 現状 `#433422` on `#f4ecd8` = 3.2:1 → 4.5:1 以上へ調整
```css
[data-theme="sepia"] {
  --bg-primary: #f4ecd8;
  --bg-secondary: #ece1c8;
  --bg-card: rgba(253, 246, 227, 0.95);      /* 透明度上げ */
  --border-color: rgba(80, 60, 25, 0.4);      /* 濃く */
  --text-main: #2d2416;                       /* 大幅に濃く (4.5:1 達成) */
  --text-muted: #5d4e37;                      /* 濃く */
  --accent-primary: #8b5e1a;                  /* 濃く */
  --accent-purple: #7a4d16;
  --accent-cyan: #3d6b5a;
  --accent-glow: rgba(139, 94, 26, 0.3);
  --accent-danger: #a03030;
  --accent-success: #2d7030;
}
```
- 検証: ブラウザ DevTools → Elements → Computed → コントラスト比確認、または `axe-core` 実行
- **検証コマンド**: `npm run test:ci -- tests/unit/a11y.test.ts` (axe 含む)
- **期待結果**: 全テキスト要素で 4.5:1 以上、UI 境界 3:1 以上

---

### Step 3: index.html 基礎メタ修正
- **対象ファイル**: `src/index.html` (修正)
- **実装内容**:
```html
<!DOCTYPE html>
<html lang="ja">  <!-- 追加 -->
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0, user-scalable=yes" />  <!-- user-scalable=yes 追加 -->
  <meta name="theme-color" content="#0a0e17" media="(prefers-color-scheme: dark)" />
  <meta name="theme-color" content="#f8fafc" media="(prefers-color-scheme: light)" />
  <meta name="theme-color" content="#f4ecd8" media="(prefers-color-scheme: no-preference)" />
  <title>AutoNovel Studio</title>
  ...
</head>
```
- **検証コマンド**: `npm run build && npx serve dist` → Lighthouse Accessibility スコア確認
- **期待結果**: `lang` 属性・拡大縮小許可・テーマカラー設定済

---

### Step 4: i18n コア構造作成
- **対象ディレクトリ**: `src/i18n/` (新規作成)
- **ファイル構成**:
```
src/i18n/
├── index.ts              # エントリーポイント・プロバイダー
├── locales/
│   ├── ja.json           # 日本語辞書 (既存UI全文)
│   └── en.json           # 英語辞書
├── useI18n.ts            # 翻訳フック (t(key, params?))
├── LocaleProvider.tsx    # Context プロバイダー
└── detectLocale.ts       # ブラウザ言語検出・localStorage 同期
```
- **ja.json 抽出方針**: 既存ハードコード文字列を `grep -r ">[^<]*[一-龯ひ-ゟァ-ヾ]" src/components --include="*.tsx"` で洗い出し、キー化
- キー命名: `common.save`, `editor.revision.apply`, `generation.status.streaming` 等 階層化
- **検証コマンド**: `npm run typecheck && npm run test:ci -- tests/unit/i18n/`
- **期待結果**: `useI18n()` で `t('common.save')` → "保存" / "Save" 切替動作

---

### Step 5: 言語切替コンポーネント
- **対象ファイル**: `src/components/common/LanguageSwitcher.tsx` (新規作成)
- **実装内容**:
  - Props: なし (内部で `useI18n()` 使用)
  - UI: ドロップダウン or セグメントセレクタ
  - 表示項目: 🇯🇵 日本語 / 🇺🇸 English (ネイティブ名併記: "日本語 / English")
  - 切替時: `setLocale('en')` → 即時全UI再レンダリング
  - 永続化: `localStorage.setItem('autonovel.locale', 'en')`
  - アクセシビリティ: `role="combobox"`, `aria-label="言語選択"`, キーボード操作対応
- **検証コマンド**: `npm run typecheck && npm run test:ci -- tests/unit/components/LanguageSwitcher.test.tsx`
- **期待結果**: 切替で全UI文字列即座切替、永続化・復元動作

---

### Step 6: App.tsx へ言語切替配置
- **対象ファイル**: `src/App.tsx` (修正)
- **変更箇所**: ヘッダー右端 (L230 付近、テーマセレクタ隣)
- **実装内容**:
  1. `LocaleProvider` で App 全体ラップ (main.tsx または App.tsx 内部)
  2. ヘッダーに `<LanguageSwitcher />` 追加
  3. 初期ロケール: `detectLocale()` → `navigator.language` 起点・localStorage 優先
- **検証コマンド**: `npm run typecheck && npm run dev` 手動確認
- **期待結果**: ヘッダーに言語切替表示、切替で全画面即時翻訳

---

### Step 7: Modal フォーカストラップ・ARIA 強化
- **対象ファイル**: `src/components/common/Modal.tsx` (修正)
- **実装内容**:
  1. `focus-trap-react` 相当の自前実装 (依存追加なし):
     - `useEffect` で `Tab` キー監視、モーダル内最初/最後要素で循環
  2. `aria-describedby` 追加: 本文コンテナに `id` 付与、モーダルに `aria-describedby` 指定
  3. 閉じる導線: Esc キー + オーバーレイクリック + 閉じるボタン + **ヘッダー「閉じる」リンク** (モバイル対応)
  4. 開閉時アナウンス: `announce('モーダルを開きました', 'polite')` (Step 10 利用)
- **検証コマンド**: `npm run typecheck && npm run test:ci`
- **期待結果**: キーボードのみでモーダル操作完結、スクリーンリーダー読み上げ正常

---

### Step 8: エディタ周りキーボード完全到達・ARIA
- **対象ファイル**: `src/components/editor/Editor.tsx` (修正)
- **対象範囲**: ツールバー・インライン推敲・サイドバー・履歴ドロワー
- **実装内容**:
  1. ツールバー: `role="toolbar"`, `aria-label="執筆ツール"`、ボタンに `aria-label`
  2. インライン推敲: `role="menu"`, `aria-label="推敲メニュー"`、項目 `role="menuitem"`
  3. サイドバー: `role="complementary"`, `aria-label="品質診断"`、見出し階層 `h2/h3`
  4. 履歴ドロワー: `role="dialog"`, `aria-label="編集履歴"`、フォーカストラップ
  5. ショートカットキー一覧: `?` キーでヘルプモーダル表示 (Cmd/Ctrl+S, Cmd/Ctrl+Z 等)
  6. `contentEditable` 内: `aria-multiline="true"`, `aria-label="本文編集エリア"`
- **検証コマンド**: `npm run test:ci -- tests/unit/a11y.test.ts` (axe + 手動到達確認)
- **期待結果**: Tab/Shift+Tab で全機能到達、スクリーンリーダーで構造理解可能

---

### Step 9: 生成UI ライブリージョン・進捗アナウンス
- **対象ファイル**: `src/components/generate/SimpleModePanel.tsx` (修正)
- **実装内容**:
  1. ステータスバー (Step 4 作成) に `aria-live="polite" aria-atomic="true"` 付与
  2. フェーズ変化時: `announce('生成を開始しました', 'polite')` / `announce('生成が完了しました', 'polite')`
  3. エラー時: `announce('生成に失敗しました。下書きを保存するか再試行してください', 'assertive')`
  4. 進捗: 10% 刻みで `announce('生成進捗 30パーセント', 'polite')` (頻度制御: 5秒以上間隔)
  5. リトライ: `announce('再試行中、2回目です', 'polite')`
- **検証コマンド**: `npm run typecheck && npm run test:ci`
- **期待結果**: スクリーンリーダーで生成状況がリアルタイム通知

---

### Step 10: 共通アナウンスユーティリティ
- **対象ファイル**: `src/utils/announce.ts` (新規作成)
- **実装内容**:
```typescript
let liveRegionPolite: HTMLDivElement | null = null;
let liveRegionAssertive: HTMLDivElement | null = null;

function ensureLiveRegions() {
  if (typeof document === 'undefined') return;
  if (!liveRegionPolite) {
    liveRegionPolite = document.createElement('div');
    liveRegionPolite.setAttribute('role', 'status');
    liveRegionPolite.setAttribute('aria-live', 'polite');
    liveRegionPolite.setAttribute('aria-atomic', 'true');
    liveRegionPolite.style.position = 'absolute';
    liveRegionPolite.style.width = '1px';
    liveRegionPolite.style.height = '1px';
    liveRegionPolite.style.overflow = 'hidden';
    document.body.appendChild(liveRegionPolite);
  }
  if (!liveRegionAssertive) {
    liveRegionAssertive = document.createElement('div');
    liveRegionAssertive.setAttribute('role', 'alert');
    liveRegionAssertive.setAttribute('aria-live', 'assertive');
    liveRegionAssertive.setAttribute('aria-atomic', 'true');
    liveRegionAssertive.style.position = 'absolute';
    liveRegionAssertive.style.width = '1px';
    liveRegionAssertive.style.height = '1px';
    liveRegionAssertive.style.overflow = 'hidden';
    document.body.appendChild(liveRegionAssertive);
  }
}

export function announce(message: string, priority: 'polite' | 'assertive' = 'polite') {
  ensureLiveRegions();
  const region = priority === 'assertive' ? liveRegionAssertive : liveRegionPolite;
  if (region) {
    region.textContent = '';
    // 次フレームで設定 (同一メッセージ連続時も読み上げさせる)
    requestAnimationFrame(() => { region.textContent = message; });
  }
}
```
- **検証コマンド**: `npm run test:ci -- tests/unit/utils/announce.test.ts`
- **期待結果**: polite/assertive 両方で読み上げ発火、重複メッセージも読み上げ

---

### Step 11: 自動・手動アクセシビリティテスト
- **対象ファイル**: `tests/unit/a11y.test.ts` (新規作成)
- **テスト内容**:
  1. **axe-core 自動検査**: `axe-core` + `jest-axe` で主要ページ (Editor, Generate, Studio, Modal) スキャン → violations ゼロ
  2. **コントラスト比**: 全テーマ (dark/light/sepia) で主要テキスト・UI境界 測定 → AA 基準クリア
  3. **キーボード到達**: `tabbable` ライブラリでフォーカス可能要素列挙 → 全インタラクティブ要素到達確認
  4. **ARIA 必須属性**: `REQUIRED_ARIA_PATTERNS` チェックリストベースで主要コンポーネント検証
  5. **言語属性**: `html[lang]` 存在・切替時更新確認
- **検証コマンド**: `npm run test:ci -- tests/unit/a11y.test.ts`
- **期待結果**: 全自動チェックパス、手動チェックリスト 100% クリア

---

### Step 12: E2E 実操作確認
- **対象ファイル**: `tests/e2e/a11y_i18n.test.ts` (新規作成)
- **シナリオ** (Playwright):
  1. **キーボードのみ操作**: Tab でヘッダー→エディタ→ツールバー→サイドバー→モーダル開閉→全機能到達
  2. **スクリーンリーダー模擬**: `page.evaluate(() => document.querySelector('[aria-live]')?.textContent)` でアナウンス取得確認
  3. **言語切替**: LanguageSwitcher で English 選択 → 全UI 英語化 → リロード後 English 維持
  4. **テーマ切替**: Dark/Light/Sepia 切替 → コントラスト比維持・永続化確認
  5. **減らされた動き**: `prefers-reduced-motion: reduce` エミュレーション → アニメーション無効化確認
  6. **ズーム**: 200% ズーム → レイアウト崩れなし・タッチターゲット 44px 維持
- **検証コマンド**: `npm run test:e2e -- tests/e2e/a11y_i18n.test.ts`
- **期待結果**: 全シナリオパス、実環境で商用レベルアクセシビリティ確認

---

## 🔗 依存関係グラフ
```
Step 1 → Step 2 → Step 3
              ↓
         Step 4 → Step 5 → Step 6
              ↓         ↓
         Step 10 ← Step 7 → Step 8 → Step 9
                            ↓
                       Step 11 → Step 12
```

---

## ✅ 完了判定基準
1. 全 12 ステップ検証コマンド通過
2. 既存テストスイート ALL GREEN
3. **Lighthouse Accessibility スコア 95+** (本番ビルドで測定)
4. **axe-core violations 0** (主要 10 ページ)
5. 手動確認: キーボードのみで全機能操作可能、NVDA/VoiceOver で構造・状態読み上げ正常
6. 言語切替・テーマ切替・減らされた動き・ズーム 200% すべて正常動作
7. TypeScript 型チェック・Lint エラーなし

---

## 📝 備考
- i18n 辞書 (ja.json/en.json) は初回作成コスト大だが、以降はキー追加のみ
- 既存ハードコード文字列は `grep -r ">[^<]*[一-龯ひ-ゟァ-ヾ]" src/components --include="*.tsx"` で機械的に抽出可能
- `focus-trap-react` 等外部ライブラリ不使用 (自前 20 行程度で実装可能・バンドルサイズ削減)
- `announce` ユーティリティは全コンポーネントで共用、今後の機能追加時も一貫した読み上げ保証
- セピアテーマ修正は色覚多様性配慮にも寄与 (プロタノピア・デューテラノピアシミュレーション確認推奨)