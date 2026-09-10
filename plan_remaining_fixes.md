# 残作業完了のための実装計画書

**対象**: GeneratePanel.tsx 構文エラー修正とビルド検証
**前提**: MSW v2 移行とビルド最適化設定は完了済み
**ステップ数**: 6ステップ（各ステップは単一の明確な動作のみ）

---

## Phase 1: GeneratePanel.tsx 構文エラー修正 (Step 1-4)

### Step 1
`frontend/src/components/GeneratePanel.tsx` を開き、line 619 付近の `)}` を `))}` に修正する
- 対象行: `                )}`
- 修正後: `                ))}`
- 理由: `Object.keys(agentProgress).map(...)` のコールバック閉じ括弧と `map` 自体の閉じ括弧が不足

### Step 2
`frontend/src/components/GeneratePanel.tsx` を開き、line 745 付近の `)}` を `))}` に修正する
- 対象行: `                )}`
- 修正後: `                ))}`
- 理由: 同じく `Object.keys(agentProgress).map(...)` の 2 回目の出現箇所

### Step 3
修正後のファイルで構文チェックを実行する
```bash
cd E:\hhh\frontend && npx esbuild src/components/GeneratePanel.tsx --loader:.tsx=tsx
```
- エラーがゼロになることを確認

### Step 4
TypeScript 型チェックを実行する
```bash
cd E:\hhh\frontend && npm run typecheck
```
- 型エラーがゼロになることを確認（GeneratePanel.tsx 関連以外の既存エラーは許容）

---

## Phase 2: ビルド・テスト検証 (Step 5-6)

### Step 5
本番ビルドを実行する
```bash
cd E:\hhh\frontend && npm run build
```
- ビルドが正常完了することを確認（dist フォルダ生成、vendor chunk 分離確認）

### Step 6
テストスイートを実行する
```bash
cd E:\hhh\frontend && npm run test:ci
```
- カバレッジ閾値を満たし、全テストがパスすることを確認
- MSW v2 移行後のハンドラ警告が出ないことを確認

---

## 実行上の注意事項

1. **Step 1-2 は慎重に** - `)}` は他の箇所にも存在するため、line 619 と line 745 のみを特定して修正
2. **修正前には必ずバックアップ** - `cp GeneratePanel.tsx GeneratePanel.tsx.bak`
3. **エラー時は直前のステップのみ再実行** - esbuild でエラーなら Step 1-2 に戻る
4. **検証コマンドは各ステップ後に必ず実行**

---

## 検証コマンド一覧

| Step | 検証コマンド | 成功基準 |
|------|-------------|----------|
| 1 | `grep -n ")}" frontend/src/components/GeneratePanel.tsx \| head -5` | line 619 が `))}` になっている |
| 2 | `grep -n ")}" frontend/src/components/GeneratePanel.tsx \| tail -5` | line 745 が `))}` になっている |
| 3 | `cd frontend && npx esbuild src/components/GeneratePanel.tsx --loader:.tsx=tsx` | エラー 0 件 |
| 4 | `cd frontend && npm run typecheck` | 型エラー 0 件（既存除く） |
| 5 | `cd frontend && npm run build` | dist/ 生成、vendor chunk 確認 |
| 6 | `cd frontend && npm run test:ci` | 全パス、MSW 警告なし |

---

## 完了条件

- [ ] line 619: `)}` → `))}` 修正済み
- [ ] line 745: `)}` → `))}` 修正済み  
- [ ] `npx esbuild` 構文エラー 0 件
- [ ] `npm run typecheck` 型エラー 0 件
- [ ] `npm run build` 正常完了（dist/ 生成）
- [ ] `npm run test:ci` 全テストパス
- [ ] MSW v2 ハンドラ警告なし
- [ ] vendor chunk 分離確認（dist/assets/vendor-*.js 存在）