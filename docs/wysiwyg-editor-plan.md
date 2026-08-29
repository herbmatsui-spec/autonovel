# Tiptap/Novel.sh風WYSIWYGエディタ統合実装計画書

## 改善案 4: 高度なWYSIWYGエディタへの刷新

autonovelは現在、ImportFormでプレーンテキストエリアを使用しています。このエディタを刷新し、Novel.shと同様の高機能WYSIWYGエディタ（Tiptapベース）に置き換えることで、Slash commands、ブロックレベルのAI補完、画像埋め込みなどの機能を追加します。

### 参考実装
1. **Novel.sh** (steven-tey/novel): NotionスタイルWYSIWYGエディタ、Tiptap + Vercel AI SDK基盤、Slash commands、AI autocomplete (`++`トリガー)、画像アップロード、LaTeXサポート
2. **Tiptapエコシステム**: `@tiptap/react`、`@tiptap/extension-*`、カスタムメニュー、ノードビュー、AI拡張
3. **Vercel AI SDK**: ストリーミングAI補完（ただしautonovelは独自バックエンドAPIを使用）

### 対象範囲
- ImportFormのテキストエリアをWYSIWYGエディタに置換
- 将来的にはChapterCardの閲覧モードから編集モードへの遷移もサポート
- ChapterCardの内容表示はHTMLレンダリングに移行
- AI補完はautonovelバックエンドの既存LLM APIをラッピング

---

## 実装ステップ（1〜72）

### フェーズ A: 基礎調査・環境準備（1-6）

1. Novel.sh GitHubリポジトリ（steven-tey/novel）のREADME、Tech Stack、実装アプローチを調査し、`docs/novel-sh-reference.md`に要点をまとめる。
2. Tiptap公式ドキュメント（tiptap.dev）のStarterKit、Extensionシステム、React統合ガイドを読み、`docs/tiptap-reference.md`に主要概念をまとめる。
3. Novel.shのコア拡張機能（SlashCommand、AI Autocompletion、ImageUpload）の実装パターンを`docs/novel-extensions.md`に抽出。
4. 現在のautonovelエディタ実装箇所（ImportForm.textarea、ChapterCard表示）を`docs/current-editor-analysis.md`に図示。
5. 必要なTiptapパッケージリストを作成し、`docs/tiptap-packages.txt`に記録：
   - `@tiptap/react`, `@tiptap/starter-kit`
   - `@tiptap/extension-placeholder`, `@tiptap/extension-bubble-menu`
   - `@tiptap/suggestion`（SlashCommands基盤）
   - `@tiptap/extension-image`（画像ハンドリング）
   - カスタム拡張用ベースパッケージ
6. 環境準備: `pnpm install @tiptap/react @tiptap/starter-kit @tiptap/extension-placeholder @tiptap/extension-bubble-menu @tiptap/suggestion @tiptap/extension-image` を実施し、依存関係確認。

### フェーズ B: Tiptapベースエディタ実装（7-15）

7. `frontend/src/components/editor/TiptapEditor.tsx` を新規作成し、基本的なTiptapエディターコンポーネントの枠組みを作成。
8. `TiptapEditor.tsx` に `useEditor` フック（`@tiptap/react`）をインポートし、空のextensions配列でEditorインスタンスを初期化。
9. StarterKit拡張を追加し、基本的なテッド編集機能（bold, italic, link等）を有効化。
10. Placeholder拡張を追加し、空エディターヒントテキストを設定可能にする。
11. エディターコンポーネントのpropsを定義: `value`（文字列）、`onChange`（文字列→void）、`placeholder`（文字列、任意）。
12. `useEffect` フックで `value` propの変更をエディター内容に反映させる実装を追加。
13. `useEffect` フックでエディター内容の変更を`onChange`コールバックに伝播させる実装を追加（debounce付き）。
14. エディターコンポーネントの基本構造（`<div className="prose-editor">`内に`<EditorContent />`）を作成。
15. Storybook風のプレビューコンポーネントを作成し、基本テキスト入出力が機能することを確認。

### フェーズ C: Slash Command実装（16-24）

16. Novel.shのSlashCommand実装パターンを参考に、`frontend/src/components/editor/extensions/SlashCommandExtension.tsx` を作成。
17. `@tiptap/suggestion` パッケージを使用し、SuggestionManagerをラップしたカスタム拡張クラスを実装。
18. トリガー文字を`/`に設定し、入力時にサジェスチョンポップアップを表示するロジックを実装。
19. サジェスチョンアイテムリストを定義（初期値: `/heading`, `/list`, `/quote`, `/codeblock`, `/image` 等）。
20. 各サジェスチョンアイテムの実装ロジック（例: `/heading` → 見出しノード挿入）を作成。
21. サジェスチョンポップアップのUIコンポーネントを作成（`frontend/src/components/editor/SlashSuggestionItem.tsx`）。
22. ポップアップのナビゲーション（↑↓キーで選択、Enterで確定、Escでキャンセル）を実装。
23. SlashCommand拡張を `TiptapEditor` の extensions 配列に組み込む。
24. エディター内で `/` を入力するとサジェスチョンメニューが表示され、選択すると対応するアクションが実行されることを確認。

### フェーズ D: Bubble Menu & 基本フォーマット（25-30）

25. `@tiptap/extension-bubble-menu` をインストールし、Bubble Menu拡張の基本実装を学ぶ。
26. `frontend/src/components/editor/BubbleMenu.tsx` を作成し、テキスト選択時に表示されるフローティングメニューを実装。
27. Bubble Menuに基本フォーマットボタンを配置: 太字（B）、斜体（I）、下線（U）、打ち消し線（S）、リンク（🔗）。
28. 各ボタンに対応するTiptapコマンドをバインド（例: 太字 → `editor.chain().focus().toggleBold().run()`）。
29. Bubble Menuの表示位置調整ロジック（選択範囲の上中央に配置）を実装。
30. テキスト選択時にBubble Menuが表示され、選択解除時に非表示になることを確認。

### フェーズ E: 画像アップロード・埋め込み（31-38）

31. `@tiptap/extension-image` をインストールし、基本画像ノード拡張の使い方を確認。
32. カスタム画像アップロードノードビューコンポーネント `ImageUploadNodeView.tsx` を作成（アップロード中プログレスバー表示）。
33. 画像アップロードハンドラ関数 `handleImageUpload` を作成（autonovelバックエンドAPI経由でファイルアップロード）。
34. Image拡張をカスタムノードビューで設定し、`ImageUploadNodeView` を使用するように設定。
35. 画像アップロードのドラッグ＆ドロップサポートをエディターに追加（`onDrop` イベントハンドラ）。
36. 画像の貼り付けサポート（`paste` イベントハンドラ）を追加し、クリップボードから画像を検出して自動アップロード。
37. Slash Commandに `/image` オプションを追加し、画像アップロードダイアログを表示する機能を実装。
38. 画像がアップロードされるとエディター内に`<img>`タグとして埋め込まれ、サイズ調整可能になることを確認。

### フェーズ F: AI補完機能（ブロックレベル） (39-48)

39. AI補完の基本概念を定義：ユーザーがテキスト選択またはカーソル位置でAIに文章生成・補完・改変を依頼する機能。
40. `frontend/src/components/editor/AICompletion.tsx` を作成し、AI補完コアロジックを実装。
41. AI補完のトリガー方法を2通り実装：
    - 方法1: `++` を入力時にインライン自動補完を開始（Novel.sh方式）
    - 方法2: テキスト選択時にBubble Menuに「AI補完」オプションを表示し、選択時にブロックレベル処理を開始
42. AI補完リクエスト用のAPIラッパー関数 `requestAICompletion` を作成（既存 `apiClient` をラップ）。
43. AI補完リクエストペイロードを定義：`{ prompt: string, context: string, type: 'continue'|'rewrite'|'expand'|'summarize' }`
44. AI補完レスポンスハンドラを実装し、ストリーミングまたは完全受信後のテキストをエディターに挿入。
45. インライン自動補完（++トリガー）の実装：カーソル前後のテキストを取得し、APIに送信して補完テキストを取得。
46. ブロックレベルAI補完の実装：選択範囲のテッテキストを取得し、指定タイプのプロンプトを構築してAPI送信。
47. AI処理中のローディングインジケーター（スピナーまたはテキスト）を表示するUIを実装。
48. AI補完結果がエディターに正しく挿入/置換されることを確認（Undo/Redo対応も考慮）。

### フェーズ G: エディターコンポーネント統合（49-57）

49. `ImportForm.tsx` のプレーンテキストエリア（`<textarea>`）を削除し、`TiptapEditor` コンポーネントに置換する。
50. `ImportForm` の `importText` / `setImportText` state を `TiptapEditor` の `value` / `onChange` にバインドする。
51. `ImportForm` の文字数表示ロジックを更新（HTMLタグを除いたプレーンテキスト長を計算）。
52. `ImportForm` のプレビュー機能を更新（エディター内容をHTMLからプレーンテキストに変換してプレビュー表示）。
53. 章閲覧コンポーネント `ChapterCard.tsx` に「編集モード」トグルボタンを追加（右上にペンアイコン）。
54. `ChapterCard` の編集モード時、`TiptapEditor` コンポーネントを表示し、章内容を編集可能にする。
55. 編集モードでの変更を保存する「保存」ボタンを実装し、バックエンドの章更新APIを呼び出す。
56. 編集モードから閲覧モードへの遷移時、変更があれば確認ダイアログを表示するロジックを追加。
57. 書き込みステップ (`WriteStep`) のフローを確認し、AI生成結果がエディターに正しく設定されることを確認。

### フェーズ H: 永続化・エクスポート・ポリッシュ（58-66）

58. エディター内容の変更を自動保存するデバウンス機能を実装（1秒遅延でバックエンドに保存）。
59. エディターのフォーカス管理を実装（タブ切換え時などに適切にフォーカスを移動）。
60. エディターのサイズ調整を実装（親コンテナのサイズ変更に追随する高さ制御）。
61. 元のテキストエリアとの後方互換性を保つため、データ形式変換ユーティリティを作成（HTML↔プレーンテキスト）。
62. エディター内容のバックエンド送信時に、画像アップロード状態を考慮した送信ロジックを実装。
63. キーボードショートカットの実装：
    - `Mod+b`: 太字
    - `Mod+i`: 斜体
    - `Mod+u`: 下線
    - `Mod+z`: 元に戻す
    - `Mod+y`: やり直す
    - `Tab`: AI補完接受（インラインモード時）
    - `Enter`: 改行（リスト継続等のスマート処理）
64. エディターの読み取り専用モードを実装（プレビュー表示や固定表示時用）。
65. エディター内のリンククリック処理を実装（外部リンクは新規タブ、内部リンクはナビゲーション）。
66. エディターのコンテキストメニュー（右クリック）をカスタマイズし、「切り取り」「コピー」「貼り付け」「フォント選択」等を提供。

### フェーズ I: テスト・品質・ドキュメント（67-72）

67. `frontend/src/components/editor/__tests__/TiptapEditor.test.tsx` を作成し、基本的なテキスト入出力テストを実装。
68. Slash Command拡張のユニットテストを作成（`/__tests__/SlashCommandExtension.test.tsx`）。
69. Bubble Menu拡張のユニットテストを作成（選択時表示・非表示時隠蔽をテスト）。
70. 画像アップロード機能の統合テストを作成（モックアップロードAPIを使用）。
71. AI補完機能の統合テストを作成（モックAI APIを使用し、テキスト挿入/置換を検証）。
72. ストーリーブック用のエディターサンプルストーリーを作成し、`docs/wysiwyg-editor-user-guide.md`に使用方法を記載。

---

## 詳細なフェーズ別説明

### フェーズ A: 基礎調査・環境準備
このフェーズでは、参考実装の詳細を理解し、必要な依存関係を特定します。Novel.shはTiptapを基盤とし、独自の拡張機能を追加しています。Tiptapの拡張システムを理解することで、autonovel固有の要件に合わせたカスタマイズが可能になります。環境準備ステップでは、実際にパッケージをインストールし、開発環境を整えます。

### フェーズ B: Tiptapベースエディターコンポーネント
Tiptapエディターの基本構造を作成します。`useEditor` フックでEditorインスタンスを生成し、StarterKitで基本機能を提供します。プレースホルダー拡張により、空状態でのヒントテキストを表示可能にします。このフェーズの目的は、テキストの基本的な入出力が機能するエディターの土台を作ることです。

### フェーズ C: Slash Command実装
Novel.shの特徴的な機能であるSlash commands（/`でメニュー表示）を実装します。Tiptapの`@tiptap/suggestion`パッケージを使用してサジェスチョンシステムを構築し、カスタムコマンドリストを定義します。各コマンドは特定のアクション（見出し挿入、リスト作成等）にマッピングされます。ポップアップUIのナビゲーションロジックも実装します。

### フェーズ D: Bubble Menu & 基本フォーマット
テキスト選択時に表示されるフローティングメニュー（Bubble Menu）を実装します。このメニューには太字、斜体などの基本フォーマットボタンを配置し、選択範囲に対して即座にフォーマットを適用できるようにします。ポップアップの位置調整と表示/非表示制御も重要な実装ポイントです。

### フェーズ E: 画像アップロード・埋め込み
画像のドラッグ＆ドロップ、貼り付け、Slash Command経由でのアップロードをサポートします。TiptapのImage拡張をカスタムノードビューでラッピングし、アップロード中のプログレス表示とアップロード完了後の`<img>`タグへの置換を実装します。autonovelバックエンドのファイルアップロードAPIをラッピングするハンドラ関数を作成します。

### フェーズ F: AI補完機能（ブロックレベル）
autonovelの核となるAI機能をエディターに統合します。Novel.shの`++`トリガー方式と、選択テキストに対するブロックレベル処理の両方を実装します。AI補完リクエストは既存の`apiClient`ラッパーを使用してバックエンドAPIに送信し、結果をエディターに挿入/置換します。ローディング状態の表示とエラーハンドリングも実装します。

### フェーズ G: エディターコンポーネント統合
作成したTiptapエディターを実際のautonovelコンポーネントに統合します。まずはImportFormのテキストエリアを置換し、次にChapterCardの編集モードへの応用を検討します。データフローの双方向バインディング（値の取得・設定）を正しく実装し、既存の機能（プレビュー、文字数表示、AI生成呼び出し等）との連携を確保します。

### フェーズ H: 永続化・エクスポート・ポリッシュ
実用的なエディターとして必要な機能を追加します。自動保存デバウンスによりユーザーの操作をバックエンドに反映させ、フォーカス管理とサイズ調整で快適な操作性を確保します。後方互換性のためのデータ変換ユーティリティ、キーボードショートカット、読み取り専用モード、リンク処理、コンテキストメニューなどを実装し、仕上げの作業を行います。

### フェーズ I: テスト・品質・ドキュメント
実装の品質を確保するためのテストを作成し、ユーザーガイドを作成します。ユニットテストと統合テストの両方を作成し、各機能が期待通りに動作することを確認します。エンドユーザー向けのドキュメントも作成し、機能の使い方を説明します。

---

## 依存関係とファイル構造

### 新規追加パッケージ（package.json）
```
"@tiptap/react": "^2.0.0",
"@tiptap/starter-kit": "^2.0.0", 
"@tiptap/extension-placeholder": "^2.0.0",
"@tiptap/extension-bubble-menu": "^2.0.0",
"@tiptap/suggestion": "^2.0.0",
"@tiptap/extension-image": "^2.0.0",
```

### 新規追加ファイル構造
```
frontend/
├── src/
│   ├── components/
│   │   ├── editor/
│   │   │   ├── TiptapEditor.tsx
│   │   │   ├── extensions/
│   │   │   │   ├── SlashCommandExtension.tsx
│   │   │   │   └── (その他カスタム拡張)
│   │   │   ├── BubbleMenu.tsx
│   │   │   ├── ImageUploadNodeView.tsx
│   │   │   ├── AICompletion.tsx
│   │   │   └── __tests__/
│   │   │       ├── TiptapEditor.test.tsx
│   │   │       └── SlashCommandExtension.test.tsx
│   │   ├── write/
│   │   │   ├── ImportForm.tsx      ← 置換対象
│   │   │   ├── ChapterCard.tsx     ← 編集モード追加
│   │   │   └── WritingForm.tsx     ← 変更なし（AI生成側）
│   │   ├── steps/
│   │   │   └── WriteStep.tsx       ← 変更なし
│   │   └── tabs/
│   │       └── WriteTab.tsx        ← 変更なし（子コンポーネント経由で影響）
│   ├── lib/
│   │   └── wysiwyg-utils.ts        ← HTML↔プレーンテキスト変換ユーティリティ
│   ├── hooks/
│   │   └─ useAICompletion.ts       ← AI補完カスタムフック
│   └── store/
│       └─ useWritingStore.ts       ← 拡張（エディター状態管理用）
└── docs/
    ├── novel-sh-reference.md
    ├── tiptap-reference.md
    ├── novel-extensions.md
    ├── current-editor-analysis.md
    ├── tiptap-packages.txt
    ├── wysiwyg-editor-plan.md      ← このファイル
    ├── wysiwyg-editor-user-guide.md
    └── PR-summary.md
```

---

## 実装上の注意点（低性能LLM向け）

1. **ステップの粒度**: 各ステップは1つのファイルの作成または1つの機能の実装に限定し、複雑なロジックを含まないようにしています。
2. **依存関係の段階的導入**: Tiptap関連パッケージはフェーズBでまとめて導入し、その後は機能ごとに1つずつ実装しています。
3. **既存コードの再利用**: 可能な限り既存の`apiClient`, `useWritingStore`, `useBookStore`等をラップして使用し、新規概念の導入を最小化しています。
4. **エラーハンドリングの段階的追加**: 最初は基本機能の実装に焦点を当て、後段階でエラーハンドリングとローディング状態を追加しています。
5. **ビジュアルフィードバックの早期実装**: ボタンのdisabled状態やローディングインジケーターなど、ユーザーが状況を理解しやすいフィードバックを早めに実装しています。
6. **テスト駆動開発の推奨**: 各機能実装後に対応するテストを作成することで、後戻りせずに前進できるようにしています。

---

## 期待される効果と次のステップ

本実装により、autonovelのエディター体験は以下のように変わります：
- プレーンテキストエリア → リッチテキストエディタ（Notion風）
- 手動装飾（太字・斜体等） → ワンクリックフォーマット適用
- 画像追加 → ドラッグ＆ドロップ・貼り付け・Slash Commandによる簡単アップロード
- AI補助 → `++`トリガーインライン補完および選択テキストブロックレベル処理
- ユーザーインターフェース → モダンで直感的な操作性

次のステップとしては、以下の機能拡張が考えられます：
- コラボレーション機能（リアルタイム共同編集）
- 高度なAI機能（文脈認識補完、スタイル転写等）
- エクスポート機能の強化（PDF, EPUB等への対応）
- カスタムスラッシュコマンドのユーザー定義機能
- 音声入力・音声読み上げ機能の統合

本ドキュメントに記載された72ステップを順に実装することで、低性能なLLMでも着実に進めていくことが可能です。各ステップは独立しており、前のステップが完了していれば次のステップに取り掛かれる設計となっています。