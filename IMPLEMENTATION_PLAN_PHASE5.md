# Phase 5: フロントエンド品質・残タスク対応 (12ステップ)

## 残タスク一覧

| ID | タスク | 優先度 | 工数 |
|----|--------|--------|------|
| 5-1 | フロントエンド ESLint エラー修正 (any型, a11y, unused) | High | 2時間 |
| 5-2 | `_build_prev_context` トークンベース切り捨て実装 | Medium | 1時間 |
| 5-3 | Storybook 導入 (ディスク容量確保後) | Low | 1時間 |
| 5-4 | フロントエンド テスト実行・修正 | Medium | 30分 |
| 5-5 | 全体カバレッジ測定・改善 | Medium | 30分 |
| 5-5 | pre-commit 全フック実行確認 | Medium | 15分 |
| 5-6 | CI パイプライン全グリーン確認 | Medium | 15分 |
| 5-7 | 文字化け最終チェック | Low | 5分 |
| 5-8 | 型チェック (mypy strict) 最終確認 | Low | 10分 |
| 5-9 | ドキュメント最終更新 | Low | 15分 |
| 5-10 | タグ v3.3.2 打ち | Low | 5分 |
| 5-11 | リリースノート作成 | Low | 15分 |
| 5-12 | 最終検証・完了報告 | Low | 10分 |

---

## Step 5-1: フロントエンド ESLint エラー修正

### 修正対象カテゴリ
1. `@typescript-eslint/no-explicit-any` - 型定義追加・`unknown` 置換
2. `jsx-a11y/label-has-associated-control` - `<label htmlFor>` または `<label><input /></label>`
3. `jsx-a11y/no-noninteractive-element-interactions` - `div` → `button` または `role="button" tabindex="0"`
4. `jsx-a11y/click-events-have-key-events` - `onKeyDown` 追加
5. `jsx-a11y/no-static-element-interactions` - インタラクティブ要素化
6. `@typescript-eslint/no-unused-vars` - `_` プレフィクスまたは削除
7. `react-hooks/exhaustive-deps` - 依存配列修正
8. `react-refresh/only-export-components` - 定数を別ファイルに分離

### 実装順序
1. 未使用変数・any型の簡単な修正から着手
2. a11y 関連修正 (アクセシビリティ重要)
3. React Hooks 依存配列修正

---

## Step 5-2: `_build_prev_context` トークンベース実装

### 現状
```python
summaries.append(f"第{ep.episode_num}話: {ep.title} - {ep.content[:200]}...")
```

### 目標
- `tiktoken` でトークン数計算
- `settings.context_window_min_reserve` 考慮
- 直近3話をトークン制限内で収める

---

## Step 5-3: Storybook 導入

ディスク容量不足のため延期済み。容量確保後に実行。

---

## Step 5-4: フロントエンド テスト実行

`npm run test:run` で vitest 実行。

---

## Step 5-5: pre-commit 全フック実行

`pre-commit run --all-files` で全チェック通過確認。

---

## Step 5-6: CI パイプライン確認

GitHub Actions で全ジョブグリーン確認。

---

## Step 5-7〜5-12: 最終確認・タグ・リリース