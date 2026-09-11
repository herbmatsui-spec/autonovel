# タイムマシン・章並び替え・IF分岐統合 実装計画書 (time.md)

本計画書は、UI/UX優先度「中」に分類された3大機能：
1. **タイムマシン (Undo/Redo・版管理)**：AI生成・置換時の心理的ハードルを劇的低下
2. **章ツリーのD&D並び替え & 進捗ゲージ**：長編小説制作におけるプロット構造調整の快適化
3. **死蔵されたIF分岐・矛盾レポートの統合**：実装済みの優良資産（ブランチ・差分・競合マージ）のStudio完全統合
を、低性能なLLMでも確実に1つずつ実装できるよう、**全36の独立した小さなマイクロステップ**に分割・定義した詳細手順書です。

---

## 全体構成とファイル配置

| フェーズ | 対象機能 | ステップ | 主な変更・作成対象ファイル |
| :--- | :--- | :--- | :--- |
| **Phase A** | タイムマシン (Undo/Redo・版管理) | Step 1 〜 12 | `types/history.ts`, `hooks/useHistoryStack.ts`, `HistoryDrawer.tsx`, `Editor.tsx`, `GeneratePanel.tsx` |
| **Phase B** | 章ツリーのD&D並び替え & 進捗ゲージ | Step 13 〜 24 | `types/index.ts`, `ChapterProgressBar.tsx`, `ChapterOutlineTree.tsx`, `useChapterReorder.ts` |
| **Phase C** | 死蔵されたIF分岐・矛盾レポートの統合 | Step 25 〜 36 | `tsconfig.json`, `BranchManagement.tsx`, `ConflictReportPanel.tsx`, `StudioWorkspace.tsx`, `Editor.tsx` |

---

## 詳細マイクロステップ（Micro-Steps 1〜36）

### 【Phase A: タイムマシン (Undo/Redo・版管理)（ステップ 1 〜 12）】
AIによる文章生成や推敲を試す際の「元の文章が消えたらどうしよう」という不安を完全に払拭するため、履歴バッファと世代管理ドロワーを構築します。

* **Step 1: 履歴スナップショットの型定義を作成**  
  - 対象ファイル: `frontend/src/types/history.ts` [新規作成]  
  - 変更内容: `EditorSnapshot` インターフェースを定義。  
    ```typescript
    export interface EditorSnapshot {
      id: string;
      ep_num: number;
      timestamp: number;
      label: string; // 例: "AI推敲前", "逆算プロット反映前", "手動保存"
      text: string;
      charCount: number;
      source: "manual" | "ai_assist" | "ai_generate" | "autosave";
    }
    ```  
  - 検証: TypeScriptの構文エラーがないこと。

* **Step 2: 型インデックスファイルからのエクスポートを追加**  
  - 対象ファイル: `frontend/src/types/index.ts`  
  - 変更内容: `export * from "./history";` を末尾に追加。  
  - 検証: 他のファイルから `import { EditorSnapshot } from "../types"` で参照できること。

* **Step 3: インメモリ Undo/Redo スタック管理フックを作成**  
  - 対象ファイル: `frontend/src/hooks/useHistoryStack.ts` [新規作成]  
  - 変更内容: 最大50段のスタックを保持するカスタムフックを実装。  
    - `canUndo: boolean`, `canRedo: boolean`  
    - `undo(): string | null` (直前の本文を返す)  
    - `redo(): string | null` (進めた本文を返す)  
    - `pushState(text: string): void` (新しい履歴を追加)  
  - 検証: Undo/Redo操作で正しくスタックポインタが移動すること。

* **Step 4: ローカルストレージ連動の版管理（スナップショット）フックを作成**  
  - 対象ファイル: `frontend/src/hooks/useSnapshotHistory.ts` [新規作成]  
  - 変更内容: 作品ID・話数ごとに最大20件のスナップショットを保存・取得・削除・復元するフックを実装。  
    - `snapshots: EditorSnapshot[]`  
    - `takeSnapshot(label: string, text: string, source: EditorSnapshot['source']): void`  
    - `restoreSnapshot(id: string): string | null`  
    - `deleteSnapshot(id: string): void`  
  - 検証: スナップショットが `localStorage` (`autonovel.snapshots.${bookId}.${epNum}`) に永続化されること。

* **Step 5: タイムマシンドロワーのベースUIを作成**  
  - 対象ファイル: `frontend/src/components/editor/HistoryDrawer.tsx` [新規作成]  
  - 変更内容: エディタ右側からスライドインするドロワーの枠組みを作成。  
    - オーバーレイ背景、ヘッダー（「⏱️ バージョン履歴・タイムマシン」）、閉じるボタン。  
    - 幅 380px、ダークグラスモーフィズムスタイル (`var(--bg-card)`)。  
  - 検証: 開閉アニメーションとEscキー検知で正しく開閉できること。

* **Step 6: HistoryDrawer にスナップショット一覧表示を実装**  
  - 対象ファイル: `frontend/src/components/editor/HistoryDrawer.tsx`  
  - 変更内容: スナップショットのカード一覧を表示。  
    - ラベルバッジ（AI推敲前: 紫、手動: 青、自動: グレー）  
    - 作成時刻（例: "11:45:20"）、文字数（例: "3,250字"）  
    - 現在の本文との文字数差分（例: "+180字" / "-45字"）  
  - 検証: 直近のスナップショットが一番上に整列して表示されること。

* **Step 7: HistoryDrawer に差分プレビュー表示を実装**  
  - 対象ファイル: `frontend/src/components/editor/HistoryDrawer.tsx`  
  - 変更内容: カードをクリックした際、下部に「選択版のプレビュー」を表示。  
    - 選択したスナップショットの本文の冒頭10行程度をスクロール表示。  
  - 検証: 復元前に内容を確認できること。

* **Step 8: HistoryDrawer に「この版に復元する」ボタンと処理を実装**  
  - 対象ファイル: `frontend/src/components/editor/HistoryDrawer.tsx`  
  - 変更内容: 「↩ このバージョンに復元」ボタンを配置。  
    - クリック時に現在の本文を「復元直前スナップショット」として自動退避した上で、選択した版の内容を反映。  
    - 完了トースト「✨ ○○（時刻）のバージョンに復元しました」を発火。  
  - 検証: 復元後に誤操作だった場合でも「復元直前」へ戻せる二重安全構造になっていること。

* **Step 9: Editor に Undo/Redo ボタンと HistoryDrawer 起動ボタンを配置**  
  - 対象ファイル: `frontend/src/components/editor/Editor.tsx`  
  - 変更内容: エディタ上部のタブバーまたはツールバーに以下を追加：  
    - `↩ 元に戻す` ボタン (`disabled={!canUndo}`)  
    - `↪ やり直す` ボタン (`disabled={!canRedo}`)  
    - `⏱️ 履歴` ボタン（クリックで `HistoryDrawer` を開く）  
  - 検証: テキスト入力時に Undo ボタンが活性化し、クリックで復元できること。

* **Step 10: Editor にキーボードショートカット (Ctrl+Z / Ctrl+Y) を接続**  
  - 対象ファイル: `frontend/src/components/editor/Editor.tsx`  
  - 変更内容: `handleKeyDown` イベントにショートカット処理を組み込み。  
    - `(e.ctrlKey || e.metaKey) && e.key === 'z'` → `handleUndo()`  
    - `(e.ctrlKey || e.metaKey) && (e.key === 'y' || (e.shiftKey && e.key === 'Z'))` → `handleRedo()`  
  - 検証: 通常のタイピング操作中にキーバインドでUndo/Redoがスムーズに動作すること。

* **Step 11: GeneratePanel のAI生成・プロット適用直前に自動スナップショット記録を連携**  
  - 対象ファイル: `frontend/src/components/GeneratePanel.tsx`  
  - 変更内容: `handleReversePlotComplete` および `syncGenerationToEditor` 実行の直前に `takeSnapshot("逆算プロット反映前", currentChapterText, "ai_generate")` を呼び出す。  
  - 検証: 逆算プロットを適用した直後に履歴を開くと、上書き前の文章が確実に残っていること。

* **Step 12: InlineAiToolbar のAI推敲置換直前に自動スナップショット記録を連携**  
  - 対象ファイル: `frontend/src/components/editor/InlineAiToolbar.tsx`  
  - 変更内容: 「✅ 選択箇所を置換」実行時に、置換前の全文をスナップショット（ラベル「AI推敲前: ○○」）として退避。  
  - 検証: AIによる文章置換後でもワンクリックで置換前の文章へロールバックできること。

---

### 【Phase B: 章ツリーのD&D並び替え & 進捗ゲージ（ステップ 13 〜 24）】
複数話にまたがる長編小説の構成をストレスなく組み替えられるよう、ドラッグ＆ドロップ並び替えと視覚的進捗バーを実装します。

* **Step 13: 章ステータスの型定義を拡張**  
  - 対象ファイル: `frontend/src/types/index.ts`  
  - 変更内容: `ChapterItem` の `status` を以下のように型拡張：  
    ```typescript
    export type ChapterStatus = "draft" | "writing" | "completed" | "polished";
    ```  
  - 検証: 既存コードへの型エラーが出ないことを確認。

* **Step 14: 章ステータス用定数テーブルを作成**  
  - 対象ファイル: `frontend/src/constants/chapterStatus.ts` [新規作成]  
  - 変更内容: 各ステータスのラベル、アイコン、カラーバッジ定義を作成。  
    - `draft`: { label: "プロット構想", icon: "⚪", color: "#94a3b8" }  
    - `writing`: { label: "執筆中", icon: "🟡", color: "#f59e0b" }  
    - `completed`: { label: "初稿脱稿", icon: "🟢", color: "#10b981" }  
    - `polished`: { label: "推敲完了", icon: "✨", color: "#a855f7" }  
  - 検証: 4種類のステータス定義が正しく参照できること。

* **Step 15: 全体進捗プログレスバーコンポーネントを作成**  
  - 対象ファイル: `frontend/src/components/studio/ChapterProgressBar.tsx` [新規作成]  
  - 変更内容: 作品全体の目標文字数（話数 × 目標文字数）に対する現在の総執筆文字数と進捗率を計算・表示するバー。  
    - 「📊 全 10 話中 4 話脱稿 / 総文字数 12,400 字 (目標 25,000 字 - 49.6%)」  
    - グラデーションバー (`linear-gradient(90deg, #38bdf8, #8b5cf6)`)。  
  - 検証: 総文字数と脱稿話数の割合がプログレスバーに正しく反映されること。

* **Step 16: ChapterOutlineTree ヘッダーに ChapterProgressBar を統合**  
  - 対象ファイル: `frontend/src/components/studio/ChapterOutlineTree.tsx`  
  - 変更内容: 章一覧タイトルの直下に `<ChapterProgressBar />` を配置。  
  - 検証: 章ツリーの上部で常に執筆進捗が一目で把握できること。

* **Step 17: 各章カードに文字数バッジを表示**  
  - 対象ファイル: `frontend/src/components/studio/ChapterOutlineTree.tsx`  
  - 変更内容: 章カード内のタイトル横に、当該章の本文文字数を計算してバッジ（例: `3,120字`）として表示。  
  - 検証: 本文をエディタで編集すると、ツリー側の文字数バッジもリアルタイムに連動更新されること。

* **Step 18: 各章カードにステータス変更ドロップダウンを実装**  
  - 対象ファイル: `frontend/src/components/studio/ChapterOutlineTree.tsx`  
  - 変更内容: カード内に小さなステータスピル（例: `🟡 執筆中`）を配置し、クリックでステータス（構想/執筆中/脱稿/推敲済）を即座にトグル・選択可能にする。  
  - 検証: ステータスを変更すると `ChapterItem.status` が更新され、進捗バーにも即座に反映されること。

* **Step 19: 章の並び替えロジック（純粋関数）を作成**  
  - 対象ファイル: `frontend/src/hooks/useChapterReorder.ts` [新規作成]  
  - 変更内容: 配列内の要素位置を入れ替えた後、`ep_num` (1, 2, 3...) とタイトル（「第○話」部分）を整然と再ナンバリングする関数 `reorderChapters(chapters, fromIndex, toIndex)` を実装。  
  - 検証: 並び替えても話数番号に重複や抜け番が生じないこと。

* **Step 20: 各章カードに上下移動ボタン (▲ / ▼) を追加**  
  - 対象ファイル: `frontend/src/components/studio/ChapterOutlineTree.tsx`  
  - 変更内容: D&Dが使えない端末や細かな操作のために、カード右端に ▲ / ▼ ボタンを配置。最上段の ▲、最下段の ▼ は適切に disabled 化。  
  - 検証: ▲ / ▼ を押すと1つ前後の章と順番が即座に入れ替わること。

* **Step 21: 章ツリーカードに HTML5 Drag and Drop を実装**  
  - 対象ファイル: `frontend/src/components/studio/ChapterOutlineTree.tsx`  
  - 変更内容:  
    - カードに `draggable={true}` を付与。  
    - `onDragStart`: ドラッグ中の章インデックスを `dataTransfer` に保持。  
    - `onDragOver`: デフォルト動作をキャンセルし、ドロップ可能状態にする。  
    - `onDrop`: ドロップ先の章インデックスを取得し、`reorderChapters` を実行。  
  - 検証: マウスドラッグで章を持ち上げて、別の章の前後へ移動できること。

* **Step 22: ドラッグ中のインジケーター表示（CSS）を追加**  
  - 対象ファイル: `frontend/src/index.css`  
  - 変更内容: `.chapter-card--dragging`, `.chapter-card--drop-target-top`, `.chapter-card--drop-target-bottom` スタイルを追加。  
    - ドロップ先の境界線にパープルの光るガイドライン (`box-shadow: 0 -2px 0 var(--accent-purple)`) を表示。  
  - 検証: どこに挿入されるかが視覚的に一目瞭然になること。

* **Step 23: 並び替え時の選択中エピソードの安全な追従処理を実装**  
  - 対象ファイル: `frontend/src/components/studio/ChapterOutlineTree.tsx`  
  - 変更内容: 編集中だった章が並び替えによって話数番号（例: 第2話→第4話）が変わっても、エディタで開いている章のフォーカスが外れないよう `currentEpNum` を新話数へ自動追従させる。  
  - 検証: 並び替えを行ってもエディタの本文が別章にすり替わらないこと。

* **Step 24: 並び替え完了時のトースト通知を発火**  
  - 対象ファイル: `frontend/src/components/studio/ChapterOutlineTree.tsx`  
  - 変更内容: 並び替え成功時に `onMessage?.("✨ 章の順序を並び替え、話数番号を自動再整列しました")` を通知。  
  - 検証: ユーザーに操作完了が明確に伝わること。

---

### 【Phase C: 死蔵されたIF分岐・矛盾レポートの統合（ステップ 25 〜 36）】
既に実装済みであるにもかかわらずアクセス不能になっているブランチ管理（IFルート分岐）と矛盾レポートパネルをStudioWorkspaceに完全接続します。

* **Step 25: パスエイリアスと依存関係の修正**  
  - 対象ファイル: `frontend/tsconfig.json` および `frontend/vite.config.ts`  
  - 変更内容: `frontend/src/components/branches/` 配下のコンポーネントが使用している `@/hooks/...`, `@/types/...` のエイリアスが正しく解決できるよう、`tsconfig.json` に `"paths": { "@/*": ["./src/*"] }`、`vite.config.ts` に `resolve: { alias: { '@': path.resolve(__dirname, './src') } }` を追加（または相対パスに統一）。  
  - 検証: `npx tsc --noEmit` でインポート解決エラーがゼロになること。

* **Step 26: BranchManagement コンポーネントのインポートと型検証**  
  - 対象ファイル: `frontend/src/components/branches/BranchManagement.tsx`  
  - 変更内容: インポートパスを点検し、欠落している型や未解決の参照を解消。  
  - 検証: 単独でコンパイルが通り、エラーが出ないこと。

* **Step 27: BranchManagement のスタイルをダークテーマに完全調和**  
  - 対象ファイル: `frontend/src/components/branches/BranchManagement.tsx`  
  - 変更内容: `fontFamily: 'sans-serif'`, 生の白地枠線を削除し、アプリ共通の `card`, `var(--bg-card)`, `var(--border-color)`, `btn btn-primary` に統一。  
  - 検証: Studioのダークモード画面にシームレスに調和すること。

* **Step 28: BranchTree のReactFlowスタイルと表示崩れの解消**  
  - 対象ファイル: `frontend/src/components/branches/BranchTree.tsx`  
  - 変更内容: ノード背景色をダークテーマ（`#1e293b`）、エッジ色をアクセントシアン（`#06b6d4`）に調整し、分岐ツリーが見やすくなるようにスタイリング。  
  - 検証: 分岐ノードが綺麗にグラフレンダリングされること。

* **Step 29: ChapterDiffViewer（章差分比較）のダークテーマ化**  
  - 対象ファイル: `frontend/src/components/branches/ChapterDiffViewer.tsx`  
  - 変更内容: 差分ビューアの追加行（グリーン: `rgba(16, 185, 129, 0.2)`）、削除行（レッド: `rgba(239, 68, 68, 0.2)`）を洗練されたシンタックスカラーに調整。  
  - 検証: 2つのIFルート間のテキスト差異が美しく横並び/インライン表示されること。

* **Step 30: ConflictReportPanel（矛盾詳細レポート）のスタイル調整**  
  - 対象ファイル: `frontend/src/components/editor/ConflictReportPanel.tsx`  
  - 変更内容: 背景とタブ（一覧 / 差分 / アクション）をアプリ共通のCSSクラスに統一し、緊急度バッジ（緊急/高/中/低）の視認性を向上。  
  - 検証: 矛盾レポートがダークテーマで美しく描画されること。

* **Step 31: StudioWorkspace のタブバーを4タブ構成へ拡張**  
  - 対象ファイル: `frontend/src/components/studio/StudioWorkspace.tsx`  
  - 変更内容: `StudioTab` 型を `"editor" | "branches" | "audit" | "multimedia"` に拡張し、上部タブバーに以下を配置：  
    - `✏️ 本文エディタ`  
    - `🌿 IF分岐ルート (Branches)`  
    - `🧠 矛盾診断レポート (Audit)`  
    - `🖼️ マルチメディア (AssetPack)`  
  - 検証: 4つのタブをスムーズに切り替えられること。

* **Step 32: StudioWorkspace に BranchManagement を接続**  
  - 対象ファイル: `frontend/src/components/studio/StudioWorkspace.tsx`  
  - 変更内容: `tab === "branches"` 時に `<BranchManagement bookId={selectedBookId} />` をレンダリング。  
  - 検証: タブをクリックすると、これまで隠れていたIF分岐ツリーとマージプレビューが画面上に表示されること。

* **Step 33: StudioWorkspace に ConflictReportPanel を接続**  
  - 対象ファイル: `frontend/src/components/studio/StudioWorkspace.tsx`  
  - 変更内容: `tab === "audit"` 時に、最新の矛盾診断レポートを表示するコンテナを実装。  
  - 検証: 矛盾診断結果の全項目・影響度・修正候補が一覧で確認できること。

* **Step 34: エディタから「この場面からIFルートを分岐」ボタンを新設**  
  - 対象ファイル: `frontend/src/components/editor/Editor.tsx`  
  - 変更内容: ツールバーに `🌿 IF分岐を作成` ボタンを追加。  
    - クリック時に「第○話の現在の下書きから新しいIFルートを作成しますか？」と確認し、作成後に自動で `branches` タブへ誘導。  
  - 検証: 本文執筆中に思いついた「もしもの展開」を即座に別ブランチとして保存できること。

* **Step 35: AI編集者（EditorialSidebar）と矛盾詳細レポートタブの相互導線を接続**  
  - 対象ファイル: `frontend/src/components/editor/EditorialSidebar.tsx`  
  - 変更内容: 右サイドバーの矛盾診断完了時に「📋 全○件の詳細レポートを開く」ボタンを表示し、クリックで `StudioWorkspace` の `audit` タブへダイレクト遷移させる。  
  - 検証: サイドバーの簡易表示から詳細レポート画面へワンクリックで移動できること。

* **Step 36: 全体結合テスト・型チェック・リグレッション検証**  
  - 実行コマンド:  
    - `cd frontend && npx tsc --noEmit` (TypeScript 型チェック)  
    - `cd frontend && npm run test` (Vitest ユニットテスト)  
  - 検証内容:  
    1. タイムマシン機能で Undo/Redo および履歴ドロワーからの復元が正常に動作するか。  
    2. 章ツリーでドラッグ＆ドロップおよび ▲/▼ ボタンによる並び替えが正常に動作し、文字数と進捗バーが更新されるか。  
    3. StudioWorkspace の `🌿 IF分岐ルート` タブと `🧠 矛盾診断レポート` タブがエラーなく表示され、操作できるか。  
    4. ビルド・型チェックにエラーが一切ないこと。

---

## 本計画書で解決されるユーザー体験（UX）の劇的変化

1. **タイムマシンによる「心理的安全性」の確立**  
   AIの提案や逆算プロットの適用を「試して、ダメなら1秒で戻せる」状態になるため、作家がAI機能を積極的に活用できるようになります。

2. **長編制作のプロット構築ストレスをゼロに**  
   章の順番をマウスで入れ替えるだけで話数番号が自動で整合され、全体の文字数達成率がバーで可視化されるため、プロのWeb小説執筆ツールとしての実用性が格段に向上します。

3. **埋もれていた最高機能（IFルート・マージ・矛盾診断）の完全復活**  
   ユーザーは「ヒロイン生存ルート」「バッドエンドルート」の複数世界線を同一作品内で手軽に並行執筆・比較・統合できるようになります。
