# GeneratePanel.tsx 構造問題の改善案 3つ

## 現状分析
orchestrated モード統合時に JSX のネスト構造が破損：
- `<>` フラグメントの不正なネスト
- `</div>` が `<>` に対応していない
- `mode === 'simple' ? ... : mode === 'reverse' ? ... : ...` の三項演算子が JSX 内で正しく閉じていない
- map クロージャは修正済み (`)}` → `))}`)

---

## 改善案 1: 完全リセット・再実装（推奨・確実）

### 方針
バックアップから元の GeneratePanel.tsx に戻し、orchestrated モード統合を**クリーンな状態で再実装**する。

### 手順
1. `GeneratePanel.tsx.bak` からリストア
2. 以下を段階的に追加：
   - `useUnifiedStreaming` import & hook 呼び出し
   - `mode` state に `'orchestrated'` 追加
   - モード切り替えボタンに「8エージェントオーケストレーション」追加
   - 既存の `{mode === 'simple' ? ... : ...}` を **三分岐関数** に分離
   - `<OrchestratedModePanel />` 別コンポーネントとして抽出

### メリット
- 構造的バグを根本解決
- コードの可読性・保守性が向上
- テストしやすい（コンポーネント分離）

### デメリット
- 手戻り作業が発生（約 30-60 分）

---

## 改善案 2: インライン修正・パッチ適用（最小工数）

### 方針
現在の破損したファイルに対し、構文エラー箇所のみを**外科手術的に修正**する。

### 修正ポイント（esbuild エラーベース）
1. **Line 669**: `/>` → 適切な JSX 閉じタグ（`<></>` の終端）
2. **Line 671**: `<>` → 正しいフラグメント開始
3. **Line 795**: `/>` → 正しい閉じタグ
4. **Line 797**: `</div>` → 対応する `<>` の終端に修正
5. **Line 835**: `</div>` → 正しい位置に移動
6. 三項演算子のネスト構造を `{mode === 'simple' ? A : mode === 'reverse' ? B : C}` 形式に統一

### メリット
- 即座にビルド通過可能
- 既存コードを最大限活用

### デメリット
- 根本的な構造問題は残る
- 将来的な保守が困難
- デバッグが困難

---

## 改善案 3: コンポーネント分離リファクタリング（中間・推奨バランス）

### 方針
orchestrated モード部分を**独立コンポーネント**として切り出し、GeneratePanel.tsx の複雑性を下げる。

### 新規作成
- `frontend/src/components/studio/OrchestratedModePanel.tsx`
  - orchestrated モード専用の UI・ロジック
  - `agentProgress`, `output`, `isActive`, `startUnified`, `cancelUnified` を props で受け取る

### GeneratePanel.tsx 修正
```tsx
// 既存の三項演算子を簡潔に
{mode === 'simple' ? (
  <SimpleModePanel ... />
) : mode === 'reverse' ? (
  <ReversePlotBuilder ... />
) : (
  <OrchestratedModePanel
    agentProgress={agentProgress}
    output={output}
    isActive={isActive}
    onStart={startUnified}
    onCancel={cancelUnified}
    // 必要な props
  />
)}
```

### メリット
- 構造問題を隔離・解決
- 単一責任原則に従う
- テスト容易性向上
- 既存 simple/reverse モードへの影響最小

### デメリット
- 新ファイル作成が必要（約 15 分）

---

## 比較・推奨

| 観点 | 案 1: 完全リセット | 案 2: インライン修正 | 案 3: コンポーネント分離 |
|------|-------------------|---------------------|------------------------|
| **確実性** | ◎ | △ | ◎ |
| **工数** | 30-60 分 | 15-30 分 | 20-40 分 |
| **保守性** | ◎ | × | ◎ |
| **リスク** | 低 | 中（再発リスク） | 低 |
| **推奨度** | ★★★ | ★ | ★★★ |

---

## 推奨: **案 3（コンポーネント分離）**

**理由**: 
- 確実性と工数のバランスが最良
- orchestrated モードが将来拡張されることを考慮
- 既存 simple/reverse モードに影響なし
- テスト・保守が容易

**即時アクション**:
1. `OrchestratedModePanel.tsx` 新規作成（既存破損コードから抽出・修正）
2. `GeneratePanel.tsx` をバックアップから復元
3. インポート・使用追加のみ実施