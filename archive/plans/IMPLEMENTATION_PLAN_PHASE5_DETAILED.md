# Phase 5 実装計画書: フロントエンド品質・ESLintエラー完全解消

## 現状分析

**ESLint エラー: 60 errors, 6 warnings**

| カテゴリ | 件数 | 対象ファイル数 |
|---------|------|---------------|
| `@typescript-eslint/no-explicit-any` | 38 | 12 |
| `jsx-a11y/label-has-associated-control` | 11 | 5 |
| `jsx-a11y/no-noninteractive-element-interactions` | 3 | 2 |
| `jsx-a11y/click-events-have-key-events` | 1 | 1 |
| `jsx-a11y/no-static-element-interactions` | 1 | 1 |
| `@typescript-eslint/no-unused-vars` | 4 | 4 |
| `react-hooks/exhaustive-deps` | 2 | 2 |
| `react-refresh/only-export-components` | 1 | 1 |

---

## 実装ステップ (全12ステップ)

### Step 5-1: `types/api.ts` - 型定義の any 撤廃
- **対象**: 14 件の `any` 型
- **アクション**: 具象インターフェース定義を追加、または `unknown` に置換
- **工数**: 30分

### Step 5-2: `lib/apiClient.ts` - APIクライアントの型安全化
- **対象**: 2 件の `any`
- **アクション**: レスポンス型をジェネリクスで定義
- **工数**: 15分

### Step 5-3: `hooks/` 全ファイル - フックの型安全化
- **対象**: `useAppActions.ts` (7件), `useBookDetails.ts` (1件), `useBooks.ts` (1件), `usePagination.ts` (1件), `useTaskStream.ts` (1件) = 11件
- **アクション**: APIレスポンス型をインポートして使用、unused import 削除
- **工数**: 30分

### Step 5-4: `components/tabs/MonitorTab.tsx` - any 型修正
- **対象**: 3 件の `any`
- **アクション**: 適切な型定義を追加
- **工数**: 15分

### Step 5-5: `components/tabs/StrategyTab.tsx` - any 型修正
- **対象**: 2 件の `any`
- **アクション**: 適切な型定義を追加
- **工数**: 10分

### Step 5-6: `components/tabs/AuditTab.tsx` - any 型修正 + Hooks 依存配列
- **対象**: 2 件の `any` + 1 warning (useEffect deps)
- **アクション**: 型定義追加、useEffect 依存配列修正
- **工数**: 15分

### Step 5-7: `components/tabs/PlanningTab.tsx` - a11y label 修正
- **対象**: 11 件の `jsx-a11y/label-has-associated-control`
- **アクション**: `<label htmlFor>` または `<label><input /></label>` に修正
- **工数**: 30分

### Step 5-8: `components/tabs/BooksTab.tsx` - a11y インタラクティブ要素修正
- **対象**: `click-events-have-key-events`, `no-static-element-interactions`
- **アクション**: `onKeyDown` 追加、役割付与 (`role="button" tabindex="0"`)
- **工数**: 15分

### Step 5-9: Dialog/Write コンポーネント - a11y 修正
- **対象**: `EasyModeDialog.tsx` (non-interactive), `ImportChapterDialog.tsx` (non-interactive), `GachaForm.tsx` (label), `ImportForm.tsx` (label), `WritingForm.tsx` (label 4箇所)
- **アクション**: 
  - `div` → `button` または `role="button" tabindex="0" onKeyDown`
  - `<label htmlFor>` 追加
- **工数**: 30分

### Step 5-10: `components/ui/button.tsx` - Fast Refresh 修正
- **対象**: 1 error (`react-refresh/only-export-components`)
- **アクション**: 定数を別ファイル `buttonVariants.ts` に分離
- **工数**: 10分

### Step 5-11: `components/tabs/StyleLabTab.tsx` - 未使用型削除 + a11y label
- **対象**: 未使用型定義 warning + 1 label error
- **アクション**: 未使用型削除、label 修正
- **工数**: 10分

### Step 5-12: 全体検証・テスト実行・コミット
- **アクション**: `npm run lint`, `npm run test:run`, 型チェック
- **工数**: 15分

---

## 合計推定工数: 約 3.5 時間

## 実装順序の理由
1. **型定義から先に修正** (`types/api.ts` → `lib/apiClient.ts` → `hooks/`) - 下流のコンポーネントで型が使えるように
2. **コンポーネント内の any 修正** - 型が揃ったら置換
3. **a11y 修正** - 機能に影響しないUI修正を後回し
4. **Fast Refresh** - 独立した修正