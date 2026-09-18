# AutoNovel UX改善計画: 日本語原稿文字数「本文／ルビ込み／出版用」切替 (全12ステップ)

**対象**: #1 日本語原稿文字数三段階切替
**目的**: ルビ除外・400字詰め換算など出版・公募規定への適合をその場で可視化
**前提**: 既存 `Editor.tsx:333-340` (カウントロジック)・`EditorPreview.tsx:17-21` (ルビ挿入・プレビュー実装済み)

---

## 📋 ステップ一覧マトリクス

| ステップ | 種別 | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | Type | `src/types/manuscript.ts` | [NEW] 文字数種別・カウント結果・設定の型定義 |
| **Step 2** | Utility | `src/utils/manuscriptCount.ts` | [NEW] 3モード計算ロジック (本文/ルビ込み/出版用) 純関数実装 |
| **Step 3** | Test | `tests/unit/utils/manuscriptCount.test.ts` | [NEW] 計算ロジック単体テスト (ルビ・媒介記号・改ページケース網羅) |
| **Step 4** | Hook | `src/hooks/useManuscriptCount.ts` | [NEW] エディタテキストから3モード同時計算・メモ化フック |
| **Step 5** | Component | `src/components/editor/ManuscriptCountBadge.tsx` | [NEW] 切替セレクタ付きバッジコンポーネント (ヘッダー/フッター配置用) |
| **Step 6** | Modify | `src/components/editor/Editor.tsx` | [MODIFY] 既存カウント表示 (L333-340) をバッジコンポーネントへ置換 |
| **Step 7** | Modify | `src/components/editor/EditorPreview.tsx` | [MODIFY] プレビュー側にも同バッジ表示 (同期) |
| **Step 8** | Config | `src/constants/manuscript.ts` | [NEW] 出版社・公募プリセット定義 (400字×30枚 等)・判定閾値 |
| **Step 9** | Component | `src/components/editor/ManuscriptTargetIndicator.tsx` | [NEW] 目標プリセット選択・進捗バー・超過警告表示コンポーネント |
| **Step 10** | Modify | `src/components/editor/Editor.tsx` | [MODIFY] 目標インジケーターをエディタ下部/サイドバーに配置 |
| **Step 11** | Test | `tests/unit/components/ManuscriptCountBadge.test.tsx` | [NEW] バッジ・インジケーター統合テスト |
| **Step 12** | E2E | `tests/e2e/manuscript_count.test.ts` | [NEW] Playwright: ルビ挿入→カウント切替→目標判定の実操作確認 |

---

## 🛠️ 各ステップ詳細手順

### Step 1: 型定義
- **対象ファイル**: `src/types/manuscript.ts` (新規作成)
- **実装内容**:
```typescript
export type CountMode = 'body' | 'withRuby' | 'publishing';

export interface ManuscriptCountResult {
  body: number;           // ルビタグ・読み・媒介記号を除いた純本文文字数
  withRuby: number;       // ルビ読み込み総文字数
  publishing: number;     // 400字詰め換算ページ数 (小数点1位)
  pages: number;          // publishing を切り上げ
  lines: number;          // 1行40字換算
  readingTimeMinutes: number; // 400字/分換算
}

export interface ManuscriptTargetPreset {
  id: string;
  label: string;          // "新人賞標準 (400字×30枚)"
  targetPages: number;    // 30
  targetChars: number;    // 12000 (400*30)
  warningThreshold: number; // 0.9 (90%で警告)
  maxPages?: number;      // 上限がある場合
}
```
- **検証コマンド**: `npx tsc --noEmit --skipLibCheck src/types/manuscript.ts`
- **期待結果**: 型エラーなし

---

### Step 2: 計算ロジック純関数
- **対象ファイル**: `src/utils/manuscriptCount.ts` (新規作成)
- **実装内容**:
```typescript
import { ManuscriptCountResult } from '../types/manuscript';

// ルビタグ除去: <ruby>漢字<rt>よみ</rt></ruby> → "漢字"
const RUBY_TAG_REGEX = /<ruby>([^<]+)<rt>[^<]+<\/rt><\/ruby>/g;
// 媒介記号除去: 《》《〈〉》等
const MEDIAL_REGEX = /[《〈〉「」『』【】〔〕]/g;

export function countManuscript(htmlOrText: string): ManuscriptCountResult {
  // 1. 本文文字数: HTMLタグ全除去 + 媒介記号除去 + 空白正規化
  const plainText = htmlOrText
    .replace(RUBY_TAG_REGEX, '$1')  // ルビ本体のみ残す
    .replace(/<[^>]+>/g, '')        // 残りタグ除去
    .replace(MEDIAL_REGEX, '')      // 媒介記号除去
    .replace(/\s+/g, '')            // 空白除去
    .length;

  // 2. ルビ込み: HTMLタグ除去のみ (ルビ読み含む)
  const withRubyText = htmlOrText
    .replace(/<ruby>([^<]+)<rt>([^<]+)<\/rt><\/ruby>/g, '$1($2)') // "漢字(よみ)"
    .replace(/<[^>]+>/g, '')
    .replace(/\s+/g, '')
    .length;

  // 3. 出版用: 本文文字数を 400字詰め換算
  const publishingPages = plainText / 400;
  const pages = Math.ceil(publishingPages);
  const lines = Math.ceil(plainText / 40);
  const readingTimeMinutes = Math.ceil(plainText / 400);

  return {
    body: plainText,
    withRuby: withRubyText,
    publishing: Number(publishingPages.toFixed(1)),
    pages,
    lines,
    readingTimeMinutes,
  };
}

// 目標判定
export function checkTarget(result: ManuscriptCountResult, preset: ManuscriptTargetPreset) {
  const ratio = result.body / preset.targetChars;
  return {
    ratio: Number(ratio.toFixed(2)),
    isOver: result.body > preset.targetChars,
    isWarning: ratio >= preset.warningThreshold && !preset.maxPages,
    isMaxOver: preset.maxPages ? result.pages > preset.maxPages : false,
    remainingChars: Math.max(0, preset.targetChars - result.body),
  };
}
```
- **検証コマンド**: `npm run test:ci -- tests/unit/utils/manuscriptCount.test.ts`
- **期待結果**: 全テストパス

---

### Step 3: 計算ロジック単体テスト
- **対象ファイル**: `tests/unit/utils/manuscriptCount.test.ts` (新規作成)
- **テストケース**:
  1. プレーンテキスト「あいうえお」 → body=5, withRuby=5, publishing=0.01
  2. ルビ付き `<ruby>漢字<rt>かんじ</rt></ruby>` → body=2, withRuby=5 ("漢字(かんじ)")
  3. 混在: 「吾輩《わがはい》は<ruby>猫<rt>ねこ</rt></ruby>である」 → body=10, withRuby=15
  4. 改行・空白混在 → 正規化後カウント
  5. 空文字 → 全ゼロ
  6. 400字境界: 399字→0.99ページ, 400字→1.00ページ, 401字→1.00ページ(切り上げ2ページ)
  6. 目標判定: 12000字目標に 10800字→warning, 12001字→over
- **検証コマンド**: `npm run test:ci -- tests/unit/utils/manuscriptCount.test.ts`
- **期待結果**: 全ケースパス

---

### Step 4: 計算フック
- **対象ファイル**: `src/hooks/useManuscriptCount.ts` (新規作成)
- **実装内容**:
```typescript
import { useMemo } from 'react';
import { useNovelContext } from '../context/NovelContext';
import { countManuscript, ManuscriptCountResult } from '../utils/manuscriptCount';

export function useManuscriptCount(): ManuscriptCountResult {
  const { currentChapterContent } = useNovelContext(); // 既存: 現在チャプターHTML取得

  return useMemo(() => {
    if (!currentChapterContent) {
      return { body: 0, withRuby: 0, publishing: 0, pages: 0, lines: 0, readingTimeMinutes: 0 };
    }
    return countManuscript(currentChapterContent);
  }, [currentChapterContent]);
}
```
- **検証コマンド**: `npm run typecheck && npm run test:ci -- tests/unit/hooks/useManuscriptCount.test.ts`
- **期待結果**: 型チェック通過、コンテキスト変更で再計算発火確認

---

### Step 5: 切替バッジコンポーネント
- **対象ファイル**: `src/components/editor/ManuscriptCountBadge.tsx` (新規作成)
- **実装内容**:
  - Props: `count: ManuscriptCountResult`, `mode: CountMode`, `onModeChange: (m: CountMode) => void`
  - 表示: セグメントセレクタ (本文/ルビ込み/出版用) + 現在値大きく表示
  - モード別表示内容:
    - `body`: "本文 12,345 字"
    - `withRuby`: "ルビ込み 15,678 字"
    - `publishing`: "400字詰め 30.9 枚 (31枚)"
  - ツールチップ: モード切替時の詳細内訳表示
  - アクセシビリティ: `role="group"`, `aria-label="文字数カウントモード"`
- **検証コマンド**: `npm run typecheck && npm run test:ci -- tests/unit/components/ManuscriptCountBadge.test.tsx`
- **期待結果**: 切替操作でモード変更コールバック発火、表示切替確認

---

### Step 6: Editor.tsx 既存カウント置換
- **対象ファイル**: `src/components/editor/Editor.tsx` (修正)
- **変更箇所**: L333-340 付近の文字数表示ロジック
- **実装内容**:
  1. `useManuscriptCount()` フック導入
  2. `const [countMode, setCountMode] = useState<CountMode>('body')` 追加
  3. 既存 `<div className="char-count">` を `<ManuscriptCountBadge count={count} mode={countMode} onModeChange={setCountMode} />` に置換
  4. `localStorage` キー `autonovel.countMode` で永続化
- **検証コマンド**: `npm run typecheck && npm run test:ci`
- **期待結果**: エディタヘッダー/フッターに新バッジ表示、モード切替・永続化動作

---

### Step 7: EditorPreview.tsx 同期表示
- **対象ファイル**: `src/components/editor/EditorPreview.tsx` (修正)
- **実装内容**:
  1. 同じ `useManuscriptCount()` 使用 (コンテキスト共有なので同一値)
  2. プレビュー右上に同バッジ配置 (Props で `compact={true}` 対応)
  3. 縦書きプレビュー時も文字数参照可能
- **検証コマンド**: `npm run typecheck && npm run test:ci`
- **期待結果**: プレビュー開閉で同一カウント表示、モード同期

---

### Step 8: 出版社・公募プリセット定義
- **対象ファイル**: `src/constants/manuscript.ts` (新規作成)
- **実装内容**:
```typescript
import { ManuscriptTargetPreset } from '../types/manuscript';

export const MANUSCRIPT_PRESETS: ManuscriptTargetPreset[] = [
  { id: 'shousetsu-gekkan', label: '小説現代・新人賞 (400字×30枚)', targetPages: 30, targetChars: 12000, warningThreshold: 0.9 },
  { id: 'shousetsu-subaru', label: '小説すばる・新人賞 (400字×50枚)', targetPages: 50, targetChars: 20000, warningThreshold: 0.9 },
  { id: 'dengeki-bunko', label: '電撃文庫・大賞 (400字×100枚)', targetPages: 100, targetChars: 40000, warningThreshold: 0.85, maxPages: 100 },
  { id: 'kakuyomu', label: 'カクヨム・コンテスト (10万字以内)', targetPages: 250, targetChars: 100000, warningThreshold: 0.9, maxPages: 250 },
  { id: 'narou', label: '小説家になろう・長編 (文字数自由)', targetPages: 0, targetChars: 0, warningThreshold: 1 },
  { id: 'custom', label: 'カスタム設定…', targetPages: 0, targetChars: 0, warningThreshold: 0.9 },
];
```
- **検証コマンド**: `npm run typecheck`
- **期待結果**: 型エラーなし、配列インポート可能

---

### Step 9: 目標インジケーターコンポーネント
- **対象ファイル**: `src/components/editor/ManuscriptTargetIndicator.tsx` (新規作成)
- **実装内容**:
  - Props: `count: ManuscriptCountResult`, `preset: ManuscriptTargetPreset`, `onPresetChange: (id: string) => void`
  - 表示:
    - セレクタ: プリセット選択 (カスタム選択時はモーダルで目標枚数入力)
    - プログレスバー: `ratio` 0-100% (緑→黄→赤グラデーション)
    - 数値: "10,800 / 12,000 字 (90%) / あと 1,200 字"
    - 超過時: 赤バー + "目標超過 +2,345 字"
    - 上限ありプリセットで超過: "上限 100枚 超過 (現在 102枚)"
  - アクセシビリティ: `role="progressbar"`, `aria-valuenow`, `aria-valuemin`, `aria-valuemax`
- **検証コマンド**: `npm run typecheck && npm run test:ci -- tests/unit/components/ManuscriptTargetIndicator.test.tsx`
- **期待結果**: 進捗バー・警告色・超過表示すべて正常動作

---

### Step 10: Editor.tsx 目標インジケーター配置
- **対象ファイル**: `src/components/editor/Editor.tsx` (修正)
- **実装内容**:
  1. `useManuscriptCount()` 取得済み `count` 使用
  2. `const [targetPresetId, setTargetPresetId] = useState('shousetsu-gekkan')` (localStorage 永続化)
  3. エディタ下部 (ツールバー上 or ステータバー) に `<ManuscriptTargetIndicator />` 配置
  4. サイドバー開閉時はサイドバー内にもミニ表示 (オプション)
- **検証コマンド**: `npm run typecheck && npm run test:ci`
- **期待結果**: 目標選択→進捗バー更新、プリセット永続化、超過時赤表示

---

### Step 11: 統合単体テスト
- **対象ファイル**: `tests/unit/components/ManuscriptCountBadge.test.tsx` (新規・Step 5 追加分)
- **追加テストケース**:
  1. `ManuscriptCountBadge` + `ManuscriptTargetIndicator` 同時マウントでカウント同期
  2. プリセット切替で進捗バー即再計算
  3. カスタム目標入力モーダル (Step 9 で実装分) 動作
  4. localStorage 永続化・復元 (ページリロードシミュレーション)
- **検証コマンド**: `npm run test:ci -- tests/unit/components/ManuscriptCountBadge.test.tsx tests/unit/components/ManuscriptTargetIndicator.test.tsx`
- **期待結果**: 全ケースパス

---

### Step 12: E2E 実操作確認
- **対象ファイル**: `tests/e2e/manuscript_count.test.ts` (新規作成)
- **シナリオ** (Playwright):
  1. エディタで本文入力 → ルビ挿入ボタンで `<ruby>薔薇<rt>ばら</rt></ruby>` 挿入
  2. バッジ「本文」モードでカウント確認 (ルビ除外)
  3. 「ルビ込み」切替 → カウント増加確認
  4. 「出版用」切替 → 400字詰め枚数表示確認
  5. 目標プリセット「新人賞標準」選択 → 進捗バー 90% で黄色警告確認
  6. さらに入力→目標超過で赤表示確認
  7. プレビュー開く → 同一カウント・同一モード表示確認
  8. ページリロード → モード・プリセット復元確認
- **検証コマンド**: `npm run test:e2e -- tests/e2e/manuscript_count.test.ts`
- **期待結果**: 全シナリオパス、実操作で差異なし

---

## 🔗 依存関係グラフ
```
Step 1 → Step 2 → Step 3
              ↓
         Step 4 → Step 5 → Step 6 → Step 7
              ↓              ↓
         Step 8 → Step 9 → Step 10
                     ↓
               Step 11 → Step 12
```

---

## ✅ 完了判定基準
1. 全 12 ステップ検証コマンド通過
2. 既存テストスイート ALL GREEN
3. 手動確認: ルビ挿入→3モード切替→目標判定→永続化の全フロー動作
4. TypeScript 型チェック・Lint エラーなし
5. アクセシビリティ: キーボード操作でモード切替・プリセット選択可能、スクリーンリーダー読み上げ確認

---

## 📝 備考
- 計算ロジックは純関数 (Step 2) に切り出し、エディタ・プレビュー・将来のエクスポート前検証でも再利用可能
- ルビ正規表現は既存 `EditorPreview.tsx` の実装と整合 (同一パターン使用)
- 400字詰め換算は日本国内出版標準準拠。将来的に設定ファイル化しやすい構造に
- カスタム目標モーダルは Step 9 内で簡易実装 (別ファイル化不要)