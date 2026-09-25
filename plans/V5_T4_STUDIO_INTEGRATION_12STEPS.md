# AutoNovel v5.0 実装計画書 T4: Studio Workspace ＆ エディタUX統合 (全12ステップ)

**対象領域**: コア設計 4 (Studio Workspace & Editor UX Integration)  
**目的**: `StudioWorkspace.tsx` のUI空洞化（章ツリー未配置・Zenモード無反応・監査パネル未配置）を解消し、日本語原稿文字数3段階切替（PLAN_UX02）をメインエディタへ完全配備する。  
**前提条件**: 各ステップは単一ファイル・単一責任で完結し、低性能なLLMでも1ステップずつ順番に適用可能。

---

## 📋 ステップ一覧マトリクス

| ステップ | 種別 | 対象ファイル | 目的・タスク |
|:---:|:---|:---|:---|
| **Step 1** | Type | `frontend/src/types/manuscript.ts` | [CHECK] 原稿カウント・目標プリセット型定義の確認・補完 |
| **Step 2** | Util | `frontend/src/utils/manuscriptCount.ts` | [CHECK] 本文/ルビ込み/出版用30枚換算ロジックの確認 |
| **Step 3** | Hook | `frontend/src/hooks/useManuscriptCount.ts` | [CHECK] メモ化フックの実装確認 |
| **Step 4** | Component | `frontend/src/components/editor/ManuscriptCountBadge.tsx` | [CHECK] 切替バッジコンポーネントのUI確認 |
| **Step 5** | Component | `frontend/src/components/editor/ManuscriptTargetIndicator.tsx` | [CHECK] 目標進捗バーコンポーネントのUI確認 |
| **Step 6** | Editor | `frontend/src/components/editor/Editor.tsx` | [MODIFY] 旧文字数表示（L369-383）を削除し、`ManuscriptCountBadge` と `ManuscriptTargetIndicator` を配置 |
| **Step 7** | Preview | `frontend/src/components/editor/EditorPreview.tsx` | [MODIFY] プレビュー側にも同期バッジを配置 |
| **Step 8** | Studio | `frontend/src/components/studio/ChapterOutlineTree.tsx` | [MODIFY] 章選択・追加・D&D並び替えのコールバック調整 |
| **Step 9** | Studio | `frontend/src/components/studio/StudioWorkspace.tsx` | [MODIFY] 左ペインに `<ChapterOutlineTree />` を正式配備（空洞化解消） |
| **Step 10** | Studio | `frontend/src/components/studio/StudioWorkspace.tsx` | [MODIFY] `layoutMode === "zen"` 時の `<ZenWritingScreen />` レンダリング実装 |
| **Step 11** | Test | `frontend/tests/components/StudioWorkspace.test.tsx` | [MODIFY] 左ペイン章ツリー・Zenモードの描画テスト追加 |
| **Step 12** | E2E | `frontend/tests/e2e/editor_ux_manuscript.test.ts` | [NEW] 原稿カウント切替と章ツリー操作のE2Eテスト |

---

## 🛠️ 各ステップ詳細手順

### Step 1: 原稿カウント型定義 (`frontend/src/types/manuscript.ts`)
- **目的**: `CountMode` ('body' | 'withRuby' | 'publishing') および `ManuscriptCountResult` の型完全性を確認。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`

---

### Step 2: 計算ロジック純関数 (`frontend/src/utils/manuscriptCount.ts`)
- **目的**: ルビ除去・ルビ込み・400字詰め換算の計算純関数がテストを通過することを確認。
- **検証コマンド**: `cd frontend && npm test frontend/tests/unit/utils/manuscriptCount.test.ts`

---

### Step 3: 計算メモ化フック (`frontend/src/hooks/useManuscriptCount.ts`)
- **目的**: 本文テキスト更新時に過剰な再計算を防ぎ、スムーズな入力を維持。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`

---

### Step 4: バッジコンポーネント確認 (`frontend/src/components/editor/ManuscriptCountBadge.tsx`)
- **目的**: クリックで「本文 / ルビ込み / 出版用枚数」を即時切り替えるバッジUIのスタイル確認。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`

---

### Step 5: 目標インジケーター確認 (`frontend/src/components/editor/ManuscriptTargetIndicator.tsx`)
- **目的**: 公募・新人賞規定（30枚/50枚）に対するプログレスバーと超過警告のスタイル確認。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`

---

### Step 6: `Editor.tsx` への正式配備 (`frontend/src/components/editor/Editor.tsx`)
- **目的**: 旧コード（`const charCount = ...` 等）を撤廃し、エディタツールバーおよびフッターに `<ManuscriptCountBadge />` と `<ManuscriptTargetIndicator />` を組み込む。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`

---

### Step 7: プレビュー側への同期 (`frontend/src/components/editor/EditorPreview.tsx`)
- **目的**: プレビューモード（ルビ表示中）でも同じカウントモードとバッジが表示されるように同期。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`

---

### Step 8: 章ツリーのコールバック調整 (`frontend/src/components/studio/ChapterOutlineTree.tsx`)
- **目的**: 親の `onSelectChapter` コールバックが正しく発火し、エディタの本文が切り替わるように調整。
- **検証コマンド**: `cd frontend && npx tsc --noEmit`

---

### Step 9: StudioWorkspace左ペイン配備 (`frontend/src/components/studio/StudioWorkspace.tsx`)
- **目的**: `aside id="character-settings-pane"` の空洞化を解消し、`<ChapterOutlineTree />` を配置して章の追加・切り替え・D&D並び替えを可能にする。
- **実装内容**:
```tsx
<aside id="character-settings-pane" className="studio-pane studio-sidebar-left" ...>
  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
    <h2 style={{ fontSize: "1.05rem", color: "var(--accent-cyan)", fontWeight: 700 }}>
      📖 章一覧 & 設定
    </h2>
    ...
  </div>
  <ChapterOutlineTree
    onSelectChapter={(epNum) => {
      setCurrentEpNum(epNum);
      handleToast(`第 ${epNum} 話を選択しました`, "info");
    }}
    onMessage={handleToast}
  />
</aside>
```
- **検証コマンド**: `cd frontend && npm run build`

---

### Step 10: 集中Zenモードの実装 (`frontend/src/components/studio/StudioWorkspace.tsx`)
- **目的**: `layoutMode === "zen"` の場合に `<ZenWritingScreen />` をレンダリングし、フルスクリーン集中執筆へ切り替える。
- **検証コマンド**: `cd frontend && npm run build`

---

### Step 11: StudioWorkspace単体テスト (`frontend/tests/components/StudioWorkspace.test.tsx`)
- **目的**: 左ペインの章ツリーの表示、Zenモードへの切り替え動作をテスト。
- **検証コマンド**: `cd frontend && npm test frontend/tests/components/StudioWorkspace.test.tsx`

---

### Step 12: エディタUX結合E2Eテスト (`frontend/tests/e2e/editor_ux_manuscript.test.ts`)
- **目的**: 本文入力 → 文字数切替 → 目標警告 → 章切替の統合操作テスト。
- **検証コマンド**: `cd frontend && npx playwright test tests/e2e/editor_ux_manuscript.test.ts`
