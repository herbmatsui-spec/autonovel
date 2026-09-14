# PLAN 12: 執筆集中モード（Zen Mode）とエディタ近代化 実装計画書（全12ステップ）

**対象**: AutoNovel v4.9.0 フロントエンドエディタ、Studioワークスペース、執筆UI/UX  
**目的**: 複雑な分析ダッシュボード（レーダーチャート、DAG、PDCAモニター）を作家の視界から整理・折りたたみ可能にし、純粋に物語執筆へ没入できる「Zen Mode（集中執筆）」と、ルビ・インライン差分提案を扱えるモダンエディタ体験を実現する。  
**前提**: 既存の高度な分析・監査機能（Studio機能）を損なうことなく、初心者・プロ作家双方がストレスなく操作できる階層的UI設計。

---

## ステップ一覧

| Step | 区分 | 対象ファイル | 概要 |
| :---: | :---: | :--- | :--- |
| **1** | 状態設計 | `frontend/src/types/editorLayout.ts` (新規) | ワークスペース表示モード（Full Studio / Split / Zen Mode）の型定義 |
| **2** | レイアウト改修 | `frontend/src/components/studio/StudioWorkspace.tsx` (修正) | 左右パネルの Collapsible（折りたたみ式ドロワー）化とワンクリック全画面切替 |
| **3** | 集中執筆画面 | `frontend/src/components/editor/ZenWritingScreen.tsx` (新規) | 余計なボタンを排し、美しい原稿用紙タイポグラフィと文字数目標のみを表示する全画面モード |
| **4** | 外観カスタマイズ | `frontend/src/components/editor/EditorThemeSelector.tsx` (新規) | 明朝/ゴシックフォント切替、行間・文字サイズ、ダーク/ペーパー/セピアテーマ切替 |
| **5** | リッチエディタ | `frontend/src/components/editor/RichNovelEditor.tsx` (新規) | Tiptap (ProseMirror) ベースのヘッドレス・リッチエディタ導入 |
| **6** | Web小説記法 | `frontend/src/lib/tiptap/rubyExtension.ts` (新規) | カクヨム/なろう記法（`\|漢字《かんじ》`、`《《傍点》》`）のリアルタイムレンダリング拡張 |
| **7** | AI編集者UI | `frontend/src/components/editor/AiCoPilotSidebar.tsx` (新規) | レーダーチャート等の難解な数値を「担当編集者（AI）からの人間味ある助言」に要約表示 |
| **8** | インライン提案 | `frontend/src/components/editor/InlineDiffSuggestion.tsx` (新規) | AIリライト案を本文中に打ち消し線・追加線で表示し、ワンクリックで「採用/破棄」するUI |
| **9** | 待ち時間演出 | `frontend/src/components/common/ProgressDelight.tsx` (新規) | 生成待ち時間にストーリーテリング思考ステップ（伏線検証中、情景描写中等）を表示 |
| **10** | 縦書きプレビュー | `frontend/src/components/editor/VerticalBookReaderModal.tsx` (新規) | 文庫本のようなページめくり・見開き体験ができる高速縦書きプレビューモーダル |
| **11** | モバイル・操作系 | `frontend/src/hooks/useEditorKeybindings.ts` (新規) | `F11` (ZenMode), `Ctrl+Space` (AI継続), `Ctrl+Enter` (校正) ショートカットとスマホ対応 |
| **12** | E2Eコンポーネントテスト | `frontend/src/components/editor/__tests__/ZenModeAndEditor.test.tsx` (新規) | モード切替、ルビ描画、インライン提案の受諾操作を検証するVitestテスト |

---

## 各ステップの詳細仕様

### Step 1: ワークスペース表示モード型定義 (`frontend/src/types/editorLayout.ts`)
* **目標**: 執筆環境のレイアウト状態を統一管理。
* **実装内容**:
  ```typescript
  export type WorkspaceLayoutMode = 'studio' | 'split' | 'zen';

  export interface EditorThemeConfig {
    theme: 'dark' | 'paper' | 'sepia' | 'cyberpunk';
    fontFamily: 'serif' | 'sans' | 'mincho';
    fontSize: 'small' | 'medium' | 'large' | 'huge';
    lineHeight: 'tight' | 'normal' | 'relaxed';
    showManuscriptGrid: boolean; // 原稿用紙風のマス目・行ガイド
  }

  export interface EditorFocusState {
    isZenMode: boolean;
    hideToolbars: boolean;
    dimBackground: boolean;
    targetWordCount: number;
    currentWordCount: number;
  }
  ```
* **受け入れ基準**: TypeScript型チェックでエラーゼロ。

---

### Step 2: StudioWorkspace の折りたたみレイアウト化 (`frontend/src/components/studio/StudioWorkspace.tsx`)
* **目標**: 左（章一覧・プロットツリー）と右（分析・監査・GraphRAG）をワンクリックで瞬時に隠せるUI。
* **実装内容**:
  - `showLeftSidebar`、`showRightSidebar` のトグルステート追加。
  - スプリットバー（ドラッグでの幅調整）と、サイドバー格納時のミニマムアイコンストリップ。
  - 画面上部にレイアウト切替ボタン群 `[📊 完全Studio] [📝 執筆重視] [🧘 集中Zen]` を設置。
* **受け入れ基準**: サイドバーを折りたたんだ際にエディタ領域が画面一杯にスムーズに広がるアニメーション。

---

### Step 3: 集中執筆「Zen Mode」コンポーネント (`frontend/src/components/editor/ZenWritingScreen.tsx`)
* **目標**: 外部の刺激を遮断し、作家が「書くこと」にのみ没頭できる全画面UI。
* **実装内容**:
  - ブラウザの Fullscreen API と連動（`F11` または ボタンで起動）。
  - ヘッダー、フッター、サイドバーを完全にフェードアウト。
  - タイピング中はマウスカーソルと下部の文字数カウンターを自動非表示化（Typewriter Focus）。
  - 画面最下部に「現在の文字数 / 目標文字数（例: 2,850 / 3,000 字）」の進行度バーを控えめに表示。
* **受け入れ基準**: フルスクリーン化時に不要なスクロールバーや他パネルが一切映らないこと。

---

### Step 4: 外観・フォントカスタマイズ (`frontend/src/components/editor/EditorThemeSelector.tsx`)
* **目標**: 長時間の執筆でも目が疲れない環境をユーザーが選択可能にする。
* **実装内容**:
  - **フォント**: 「Noto Serif JP（明朝体）」「Noto Sans JP（ゴシック体）」「Shippori Mincho」。
  - **ペーパーモード**: 白背景ではなく、上質紙のような落ち着いたオフホワイト（#F7F4EB）と墨色テキスト。
  - **ダークモード**: コントラストを抑えたダークグレー（#1E1E22）。
  - **原稿用紙モード**: 縦書き400字詰めのマス目を薄く背景レンダリング。
* **受け入れ基準**: テーマ切替がLocalStorageに記憶され、即座にエディタに反映されること。

---

### Step 5: Tiptap リッチエディタ基盤の統合 (`frontend/src/components/editor/RichNovelEditor.tsx`)
* **目標**: 素の `<textarea>` からモダンなヘッドレスリッチエディタへの移行。
* **実装内容**:
  - `@tiptap/react`, `@tiptap/starter-kit` を導入。
  - 段落（Paragraph）、見出し、会話文ブロックのセマンティック構造化。
  - 行頭一字下げ（日本の小説の字下げルール）の自動インデントサポート。
* **受け入れ基準**: キーボード入力、Backspace、Undo/Redoがネイティブ以上の快適さで動作すること。

---

### Step 6: Web小説ルビ・傍点拡張の実装 (`frontend/src/lib/tiptap/rubyExtension.ts`)
* **目標**: なろう・カクヨム形式のルビ記法を編集画面上で視覚的にレンダリング。
* **実装内容**:
  - カクヨム記法: `|小説《ライトノベル》` → `<ruby>小説<rt>ライトノベル</rt></ruby>`
  - なろう記法: `漢字(かんじ)` または `|漢字《かんじ》`
  - 傍点記法: `《《ここを強調》》` → `<span class="novel-emphasis">ここを強調</span>`
  - テキストコピー時には自動的に元の記号付きテキストへ再変換。
* **受け入れ基準**: 入力中にルビが漢字の頭上に小さく綺麗に表示されること。

---

### Step 7: AI専属編集者サイドバー (`frontend/src/components/editor/AiCoPilotSidebar.tsx`)
* **目標**: レーダーチャートやAudit数値を「親身な担当編集者のアドバイス」に擬人化・要約。
* **実装内容**:
  - 「担当編集：真央（まお）」のアバター表示。
  - 「第2話の読後感チェック：冒頭の掴みは完璧です！ただ、中盤で敵との戦闘が少し説明的になっています。セリフをあと1つ足すと緊張感が出ますよ。」
  - 「ワンクリックでこの修正を適用する」クイックアクションボタンの配置。
* **受け入れ基準**: 難解な技術メトリクス（Tension Curve, Erotic Density等）が自然な日本語アドバイスに変換されて表示されること。

---

### Step 8: インラインAI変更提案（Track Changes）UI (`frontend/src/components/editor/InlineDiffSuggestion.tsx`)
* **目標**: AIが提案したリライト案を Google Docs のようにエディタ上で対話的に採択。
* **実装内容**:
  - 削除される文章には赤色の打ち消し線（Strikethrough）。
  - 新しく追加される文章には緑色の下線（Insert）。
  - 提案ブロックの横に `[✔ 反映]` `[✖ 破棄]` のフローティングボタンを表示。
* **受け入れ基準**: `[✔ 反映]` を押すと差分が本文にスムーズに統合され、`[✖ 破棄]` で元の文章に戻ること。

---

### Step 9: 待ち時間の思考プロセス演出 (`frontend/src/components/common/ProgressDelight.tsx`)
* **目標**: 1話生成の30〜60秒の待ち時間を、作家を退屈させない「ワクワクする体験」に変える。
* **実装内容**:
  - 単純なスピナーの廃止。
  - 「🧠 主人公の心理的葛藤を設計中... (25%)」
  - 「⚡ 伏線の整合性を過去ログと照合中... (50%)」
  - 「✍️ クライマックスのカタルシスを描写中... (80%)」
  - 「✨ 誤字脱字と文体リズムを最終推敲中... (95%)」
  - 進行に合わせたスムーズなプログレスリングとマイクロインタラクション。
* **受け入れ基準**: 生成中の進捗イベント（SSE）に応じてリアルタイムにメッセージと進捗率が変化すること。

---

### Step 10: 縦書き文庫本ビューア (`frontend/src/components/editor/VerticalBookReaderModal.tsx`)
* **目標**: 電子書籍リーダーや紙の文庫本で読んでいるような読書体験。
* **実装内容**:
  - CSS `writing-mode: vertical-rl` を用いた本格的な日本語縦書き組版。
  - ページ送りアニメーション（キーボード左右キー または タップ/スワイプ）。
  - 禁則処理（句読点や閉じカッコが行頭に来ない処理）。
  - ルビ・傍点・挿絵画像の縦書き内完全インライン表示。
* **受け入れ基準**: 縦書き表示時に文字崩れがなく、左右キーでスムーズにページ送りできること。

---

### Step 11: モバイル最適化とキーボード操作系 (`frontend/src/hooks/useEditorKeybindings.ts`)
* **目標**: スマホでの推敲操作と、PCでのプロ向けショートカットの両立。
* **実装内容**:
  - `F11`: Zen Mode のトグル切り替え。
  - `Ctrl + Enter`: AI推敲・校正の実行。
  - `Ctrl + Space`: AIによる続きの文の自動サジェスト。
  - モバイル画面（幅768px以下）では下部に固定された「クイック推敲バー」を提供。
* **受け入れ基準**: キー入力で各種機能が正しくトリガーされ、スマートフォンでも画面が横スクロールしないこと。

---

### Step 12: VitestによるUI/UXコンポーネントテスト (`frontend/src/components/editor/__tests__/ZenModeAndEditor.test.tsx`)
* **目標**: 新設されたUI機能の動作信頼性を担保。
* **実装内容**:
  - Zen Mode への切り替え時にサイドバー要素がDOMから非表示になることをテスト。
  - ルビ構文を入力した際に正しい `<ruby>` タグがレンダリングされることを検証。
  - インライン差分の採択ボタンクリックで本文が正しく更新されることを検証。
* **受け入れ基準**: `npm test frontend/src/components/editor/__tests__/ZenModeAndEditor.test.tsx` が PASS すること。
