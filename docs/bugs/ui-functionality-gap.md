# UI ⇄ Functionality Gap Tracking (Issue Template)

本ドキュメントは前段の検証で見つかった 14 件の「機能とUI/UX がきちんとつながっていない」項目を Issue 形式で追跡する。各項目に severity・影響範囲・関連ファイルパスを併記し、計画書 `ui-functionality-gap-plan.md` の 36 ステップとリンクする。

最終更新: 2026-09-05

---

## ✅ チェック凡例
- `[ ]` 未着手
- `[WIP]` 作業中
- `[x]` 完了 (関連ステップ番号を併記)

---

## 🔴 Critical (機能が意図通りに動かない / API不一致)

### BUG-01: `StudioWorkspace` で `tab` 状態と UI が不整合
- **Severity**: 🔴 Critical
- **影響**: `AssetPackPanel` (画像生成等の重い機能) がデッドコード化
- **関連ファイル**:
  - `frontend/src/components/studio/StudioWorkspace.tsx:14-27` (tab state 定義)
  - `frontend/src/components/studio/StudioWorkspace.tsx:199` (multimedia 分岐)
- **関連ステップ**: Step 4-7
- **チェック**: [x] (Step 4-7)

### BUG-02: `promote` レスポンスの `state_token` / `redirect_url` を無視
- **Severity**: 🔴 Critical
- **影響**: 仕様意図からの逸脱、昇格フロー不完全
- **関連ファイル**:
  - `frontend/src/components/ExportPanel.tsx:60-66` (handlePromote)
  - `src/services/promotion_service.py:56-62` (redirect_url 生成)
  - `src/backend/routers/easy_mode.py:390-401` (promote endpoint)
- **関連ステップ**: Step 8-11
- **チェック**: [x] (Step 8-11)

### BUG-03: Easy ⇄ Studio の本文二重管理
- **Severity**: 🔴 Critical
- **影響**: 編集内容の往復経路が複雑、二重編集
- **関連ファイル**:
  - `frontend/src/context/NovelContext.tsx` (currentChapterText + currentOutput)
  - `frontend/src/components/ExportPanel.tsx:39, 140-145` (displayOutput, Editor onChange)
  - `frontend/src/hooks/useStreamingWriter.ts:111-116` (currentOutput 設定)
  - `frontend/src/hooks/useNovelGeneration.ts` (currentOutput 設定)
  - `frontend/src/types/index.ts:34-42` (GenerationState interface)
- **関連ステップ**: Step 12-17
- **チェック**: [x] (Step 12-17)

### BUG-04: `AssetPackPanel` (`/multimedia`) のランディング導線なし
- **Severity**: 🔴 Critical
- **影響**: 画像生成機能へ到達不能
- **関連ファイル**:
  - `frontend/src/components/studio/StudioWorkspace.tsx:14` (StudioTab 型)
  - `frontend/src/components/AssetPackPanel.tsx`
  - `frontend/src/App.tsx` (header に該当ボタンなし)
- **関連ステップ**: Step 4-7, 31-33
- **チェック**: [x] (Step 4-7, 31-33)

---

## 🟠 Major (UI 上は存在するが動かない/誤解を招く)

### BUG-05: ジャンル ⇄ Preset マッピング不備 (VRMMO/SlowLife/Zarma 到達不能)
- **Severity**: 🟠 Major
- **影響**: UI 上選択可能だが実 preset は fallback に集約
- **関連ファイル**:
  - `frontend/src/components/GeneratePanel.tsx:280-287` (ジャンル選択肢)
  - `src/backend/routers/easy_mode.py:88` (genre_key 決め打ち)
- **関連ステップ**: Step 21-24
- **チェック**: [x] (Step 21-24)

### BUG-06: `ReversePlotBuilder` 完了時に既存章データが消える可能性
- **Severity**: 🟠 Major
- **影響**: ユーザーデータ消失リスク
- **関連ファイル**:
  - `frontend/src/components/GeneratePanel.tsx:154-173` (handleReversePlotComplete)
- **関連ステップ**: Step 25-27
- **チェック**: [x] (Step 25-27)

### BUG-07: `Editor` (Studio側) の `keydown Ctrl+S` が no-op (嘘トースト)
- **Severity**: 🟠 Major
- **影響**: UX 信頼性の低下 (ミスリーディング)
- **関連ファイル**:
  - `frontend/src/components/editor/Editor.tsx:117-119`
- **関連ステップ**: Step 18, 30
- **チェック**: [x] (Step 18, 30)

### BUG-08: `StreamingWriter` のフォールバックがエラー隠蔽
- **Severity**: 🟠 Major
- **影響**: 接続失敗と成功の区別がつかない
- **関連ファイル**:
  - `frontend/src/hooks/useStreamingWriter.ts:135-153` (catch ブロック)
- **関連ステップ**: Step 19
- **チェック**: [x] (Step 19)

---

## 🟡 Minor (UX 一貫性)

### BUG-09: サイドバーヘルプのヒント文と現状の乖離
- **Severity**: 🟡 Minor
- **影響**: ユーザーが現状を把握しづらい
- **関連ファイル**:
  - `frontend/src/App.tsx:34-37` (キャッチコピー)
  - `frontend/src/components/studio/StudioWorkspace.tsx:133-138` (ヒント文)
- **関連ステップ**: Step 20
- **チェック**: [x] (Step 20)

### BUG-10: 未使用 hook の放置 (useCollabSync, useLocalDraft, usePatchReviews)
- **Severity**: 🟡 Minor
- **影響**: コードベース肥大、可読性低下
- **関連ファイル**:
  - `frontend/src/hooks/useCollabSync.ts`
  - `frontend/src/hooks/useLocalDraft.ts`
  - `frontend/src/hooks/usePatchReviews.ts`
- **関連ステップ**: Step 28-30
- **チェック**: [x] (Step 28-30)

### BUG-11: かんたんモード ⇄ Studio モードの状態分離が不完全
- **Severity**: 🟡 Minor
- **影響**: モード切替時の意図しないデータ共有
- **関連ファイル**:
  - `frontend/src/context/NovelContext.tsx` (モード横断 state)
  - `frontend/src/components/GeneratePanel.tsx:154-173` (昇格フロー)
- **関連ステップ**: Step 12-17 (Phase 3 で間接的に解決)
- **チェック**: [x] (Step 12-17 経由)

### BUG-12: `displayOutput` のフォールバック参照が古い
- **Severity**: 🟡 Minor
- **影響**: 編集→反映の遅延/不整合
- **関連ファイル**:
  - `frontend/src/components/ExportPanel.tsx:39`
- **関連ステップ**: Step 16
- **チェック**: [x] (Step 16)

### BUG-13: `GenerationState.currentOutput` が型レベルで不要
- **Severity**: 🟡 Minor
- **影響**: コード重複・責任分散
- **関連ファイル**:
  - `frontend/src/types/index.ts:34-42`
  - 関連フック/コンポーネントすべて
- **関連ステップ**: Step 17
- **チェック**: [x] (Step 17)

### BUG-14: スタイル抽出・ASCII設定等のサブ機能が Easy 配下に集約
- **Severity**: 🟡 Minor
- **影響**: Studio ユーザーから到達できない機能あり
- **関連ファイル**:
  - `frontend/src/components/GeneratePanel.tsx` (showStyleModal)
  - `frontend/src/App.tsx` (該当ボタンなし)
- **関連ステップ**: Step 31-33 (間接的に対応)
- **チェック**: [x] (Step 31-33 経由)

---

## 📋 関連ファイル一覧 (Step 2 で抽出)

### Backend
| ファイル | 関連バグ |
|---------|---------|
| `src/backend/routers/easy_mode.py` | BUG-01, BUG-05 |
| `src/backend/routers/editor.py` | BUG-01 |
| `src/services/promotion_service.py` | BUG-02 |
| `src/domain/entities/easy_mode.py` | BUG-05 |
| `src/backend/server.py` | BUG-02 (router include) |

### Frontend
| ファイル | 関連バグ |
|---------|---------|
| `frontend/src/App.tsx` | BUG-04, BUG-09, BUG-14 |
| `frontend/src/context/NovelContext.tsx` | BUG-03, BUG-11 |
| `frontend/src/components/studio/StudioWorkspace.tsx` | BUG-01, BUG-04, BUG-09 |
| `frontend/src/components/GeneratePanel.tsx` | BUG-05, BUG-06, BUG-11, BUG-14 |
| `frontend/src/components/ExportPanel.tsx` | BUG-02, BUG-03, BUG-12 |
| `frontend/src/components/editor/Editor.tsx` | BUG-07 |
| `frontend/src/hooks/useStreamingWriter.ts` | BUG-03, BUG-08 |
| `frontend/src/hooks/useNovelGeneration.ts` | BUG-03 |
| `frontend/src/hooks/useCollabSync.ts` | BUG-10 |
| `frontend/src/hooks/useLocalDraft.ts` | BUG-10 |
| `frontend/src/hooks/usePatchReviews.ts` | BUG-10 |
| `frontend/src/types/index.ts` | BUG-03, BUG-13 |
| `frontend/src/types/reversePlot.ts` | BUG-06 |

---

## 🧪 ベースライン情報 (Step 3 で記録)

- ベースライン測定日: 2026-09-05
- フロントエンド単体テスト baseline: **14 test files / 48 tests / 46 pass / 2 fail**
- 既存 fail テスト: `tests/components/GeneratePanel.test.tsx` の 2 件 (`polls task until completed when task_id is returned`, `handles failed polling status`) → 本計画の対象外として記録
- 修正後測定 (Step 34): **15 test files / 52 tests / 50 pass / 2 fail** (既存 fail と同数、新規 4 件すべて pass)

## ✅ 完了サマリ

| Phase | ステップ | 状態 |
|-------|---------|------|
| 0 準備 | 1-3 | ✅ |
| 1 Studioタブ | 4-7 | ✅ |
| 2 Promote | 8-11 | ✅ |
| 3 単一ソース | 12-17 | ✅ |
| 4 嘘UI是正 | 18-20 | ✅ |
| 5 ジャンル | 21-24 | ✅ |
| 6 ReversePlot | 25-27 | ✅ |
| 7 hook整理 | 28-30 | ✅ |
| 8 AssetPack | 31-33 | ✅ |
| 9 検証 | 34-36 | ✅ |

**14/14 BUG 修正完了・36/36 ステップ完了**

---

## 📝 進捗管理ルール

1. 各ステップ実装完了時、本ファイルの該当 BUG のチェックを `[x]` 化
2. ステップ番号を併記 (例: `[x] (Step 4)`)
3. 関連 PR 番号があれば併記 (例: `[x] (Step 4, PR #123)`)
4. 修正後に新たな問題が見つかった場合は本ファイル末尾に追記

---

## 🔍 Step 2 詳細調査ログ (2026-09-05)

`rg` による実コードベース確認結果:

### `AssetPackPanel` の参照箇所
- `frontend/src/components/studio/StudioWorkspace.tsx:7, 199` のみ (Studio タブからのみ)
- ヘッダ・かんたんモードからは到達不能 → **BUG-04 確認**

### 未使用 hook の調査
- `useCollabSync`: 定義のみ。`ConflictModal.tsx:2` で型 `ConflictSection` を import しているが、hook 自体の呼び出しは無し
- `useLocalDraft`: 定義のみ、呼び出し無し → **BUG-10 確認**
- `usePatchReviews`: 定義のみ、`usePatchReviews.ts:68` で再エクスポートしているだけ、呼び出し無し → **BUG-10 確認**

### `currentOutput` の参照箇所 (Phase 3 対象)
- 型定義: `frontend/src/types/index.ts:38`
- 初期値: `frontend/src/context/NovelContext.tsx:44`
- setter 呼び出し:
  - `frontend/src/context/NovelContext.tsx:134` (syncGenerationToEditor)
  - `frontend/src/components/ExportPanel.tsx:143` (Editor onChange)
  - `frontend/src/hooks/useStreamingWriter.ts:115` (SSE 完了)
  - `frontend/src/hooks/useNovelGeneration.ts:72, 101` (生成完了)
- getter 呼び出し: `frontend/src/components/ExportPanel.tsx:39` のみ → **BUG-03 確認**

### 嘘トースト
- `frontend/src/components/editor/Editor.tsx:115, 119` → **BUG-07 確認**